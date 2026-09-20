"""Quantile Regression Forest workflow for digital soil organic carbon mapping.

The workflow is adapted from the public Florida grazing SOC QRF repository while
keeping data sources, spatial grouping, soil depth, and model calibration specific
to Ethiopia and Kenya.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import fcluster, linkage
from scipy.spatial.distance import squareform
from sklearn.ensemble import RandomForestRegressor
from sklearn.feature_selection import RFECV
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.preprocessing import StandardScaler
from statsmodels.stats.outliers_influence import variance_inflation_factor


DEFAULT_QUANTILES = tuple(range(5, 100, 5))
DEFAULT_PARAM_GRID = {
    "n_estimators": [200, 400, 600],
    "max_depth": [10, 20, 30],
    "min_samples_split": [2, 5, 10],
    "min_samples_leaf": [1, 2, 4],
    "max_features": [0.5, 0.7, 1.0],
}


@dataclass(frozen=True)
class QRFWorkflowConfig:
    outer_cv: int = 5
    inner_cv: int = 3
    correlation_distance_threshold: float = 0.2
    vif_threshold: float = 10.0
    rfecv_step: int = 1
    rfecv_min_fraction: float = 0.10
    rfecv_min_absolute: int = 8
    random_state: int = 42
    scale_numeric_features: bool = True
    quantiles: tuple[int, ...] = DEFAULT_QUANTILES
    minimum_soc_depth_cm: float = 30.0

    def __post_init__(self) -> None:
        if self.minimum_soc_depth_cm < 30.0:
            raise ValueError("VM0042 SOC quantification depth must be at least 30 cm")
        if self.outer_cv < 2 or self.inner_cv < 2:
            raise ValueError("Cross validation fold counts must be at least two")
        if not 0.0 < self.correlation_distance_threshold <= 1.0:
            raise ValueError("Correlation distance threshold must be in the interval zero to one")
        if self.vif_threshold <= 1.0:
            raise ValueError("VIF threshold must be greater than one")


def _safe(values: Iterable[float]) -> np.ndarray:
    return np.asarray(tuple(values), dtype=float).ravel()


def _linear_trend_slope(values: np.ndarray) -> float:
    values = _safe(values)
    time = np.arange(values.size, dtype=float)
    mask = np.isfinite(values)
    if mask.sum() < 2:
        return float("nan")
    x = time[mask]
    y = values[mask]
    variance = float(np.var(x))
    if variance == 0.0:
        return float("nan")
    return float(np.cov(x, y, bias=True)[0, 1] / variance)


def _autocorr(values: np.ndarray, lag: int) -> float:
    values = _safe(values)
    if values.size <= lag:
        return float("nan")
    x = values[:-lag]
    y = values[lag:]
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() < 2:
        return float("nan")
    x = x[mask] - np.mean(x[mask])
    y = y[mask] - np.mean(y[mask])
    denominator = float(np.sqrt(np.sum(x**2) * np.sum(y**2)))
    if denominator == 0.0:
        return float("nan")
    return float(np.sum(x * y) / denominator)


def _seasonality_index(values: np.ndarray, months_in_year: int = 12) -> float:
    values = _safe(values)
    if values.size < months_in_year or values.size % months_in_year != 0:
        return float("nan")
    matrix = values.reshape(values.size // months_in_year, months_in_year)
    monthly_means = np.nanmean(matrix, axis=0)
    overall_mean = float(np.nanmean(values))
    if not np.isfinite(overall_mean) or overall_mean == 0.0:
        return float("nan")
    return float((np.nanmax(monthly_means) - np.nanmin(monthly_means)) / overall_mean)


def _interannual_stats(values: np.ndarray, months_in_year: int = 12) -> tuple[float, float]:
    values = _safe(values)
    if values.size < months_in_year or values.size % months_in_year != 0:
        return float("nan"), float("nan")
    matrix = values.reshape(values.size // months_in_year, months_in_year)
    yearly_means = np.nanmean(matrix, axis=1)
    if yearly_means.size < 2:
        return float("nan"), float("nan")
    std = float(np.nanstd(yearly_means, ddof=1))
    mean = float(np.nanmean(yearly_means))
    cv = std / mean if np.isfinite(mean) and mean != 0.0 else float("nan")
    return std, float(cv)


def _fourier_amp_phase(
    values: np.ndarray,
    harmonic: int,
    months_in_year: int = 12,
) -> tuple[float, float]:
    values = _safe(values)
    time = np.arange(values.size, dtype=float)
    mask = np.isfinite(values)
    if mask.sum() < 3:
        return float("nan"), float("nan")
    time = time[mask]
    y = values[mask]
    angular_frequency = 2.0 * pi * harmonic / months_in_year
    design = np.column_stack(
        [np.cos(angular_frequency * time), np.sin(angular_frequency * time)]
    )
    coefficients, _, _, _ = np.linalg.lstsq(design, y, rcond=None)
    amplitude = float(np.sqrt(coefficients[0] ** 2 + coefficients[1] ** 2))
    phase = float(np.arctan2(coefficients[1], coefficients[0]))
    return amplitude, phase


def compute_common_ts_features(
    values: Iterable[float],
    months_in_year: int = 12,
) -> dict[str, float]:
    """Reproduce transferable time series features from the reference workflow."""

    x = _safe(values)
    finite = x[np.isfinite(x)]
    if finite.size == 0:
        return {name: float("nan") for name in (
            "mean", "std", "cv", "min", "max", "range", "trend_slope_per_month",
            "autocorr_lag1", "autocorr_lag12", "q20", "q80", "frac_below_q20",
            "frac_above_q80", "integral_sum", "sma_anomaly_sum", "seasonality_index",
            "interannual_std", "interannual_cv", "fourier1_amplitude",
            "fourier1_phase_rad", "fourier2_amplitude", "fourier2_phase_rad"
        )}

    mean = float(np.nanmean(x))
    std = float(np.nanstd(x, ddof=1)) if finite.size > 1 else float("nan")
    q20 = float(np.nanpercentile(x, 20))
    q80 = float(np.nanpercentile(x, 80))
    count = int(np.isfinite(x).sum())
    interannual_std, interannual_cv = _interannual_stats(x, months_in_year)
    amp1, phase1 = _fourier_amp_phase(x, 1, months_in_year)
    amp2, phase2 = _fourier_amp_phase(x, 2, months_in_year)

    return {
        "mean": mean,
        "std": std,
        "cv": std / mean if np.isfinite(std) and mean != 0.0 else float("nan"),
        "min": float(np.nanmin(x)),
        "max": float(np.nanmax(x)),
        "range": float(np.nanmax(x) - np.nanmin(x)),
        "trend_slope_per_month": _linear_trend_slope(x),
        "autocorr_lag1": _autocorr(x, 1),
        "autocorr_lag12": _autocorr(x, 12),
        "q20": q20,
        "q80": q80,
        "frac_below_q20": float(np.sum(x < q20) / count),
        "frac_above_q80": float(np.sum(x > q80) / count),
        "integral_sum": float(np.nansum(x)),
        "sma_anomaly_sum": float(np.nansum(x - mean)),
        "seasonality_index": _seasonality_index(x, months_in_year),
        "interannual_std": interannual_std,
        "interannual_cv": interannual_cv,
        "fourier1_amplitude": amp1,
        "fourier1_phase_rad": phase1,
        "fourier2_amplitude": amp2,
        "fourier2_phase_rad": phase2,
    }


def correlation_cluster_select(
    features: pd.DataFrame,
    distance_threshold: float = 0.2,
) -> tuple[list[str], pd.DataFrame]:
    """Select one representative per absolute Pearson correlation cluster."""

    numeric = features.select_dtypes(include=[np.number]).copy()
    numeric = numeric.loc[:, numeric.nunique(dropna=True) > 1]
    numeric = numeric.T.drop_duplicates().T
    if numeric.shape[1] <= 1:
        columns = list(numeric.columns)
        return columns, pd.DataFrame({"variable": columns, "cluster": [1] * len(columns)})

    correlation = numeric.corr(method="pearson").clip(-1.0, 1.0).fillna(0.0)
    distance = 1.0 - np.abs(correlation.to_numpy())
    np.fill_diagonal(distance, 0.0)
    distance = 0.5 * (distance + distance.T)
    linked = linkage(squareform(distance, checks=True), method="average")
    clusters = fcluster(linked, t=distance_threshold, criterion="distance")
    assignment = pd.DataFrame({"variable": numeric.columns, "cluster": clusters})

    representatives = []
    for _, group in assignment.groupby("cluster", sort=True):
        columns = group["variable"].tolist()
        missing_fraction = numeric[columns].isna().mean()
        representatives.append(str(missing_fraction.sort_values().index[0]))
    return representatives, assignment


def vif_filter(
    features: pd.DataFrame,
    threshold: float = 10.0,
    minimum_features: int = 1,
) -> tuple[list[str], pd.DataFrame]:
    """Iteratively remove the variable with the largest VIF."""

    numeric = features.select_dtypes(include=[np.number]).copy()
    numeric = numeric.replace([np.inf, -np.inf], np.nan)
    numeric = numeric.fillna(numeric.median(numeric_only=True))
    columns = list(numeric.columns)
    history = []

    while len(columns) > minimum_features:
        matrix = StandardScaler().fit_transform(numeric[columns])
        vifs = [float(variance_inflation_factor(matrix, i)) for i in range(len(columns))]
        max_index = int(np.nanargmax(vifs))
        max_vif = vifs[max_index]
        history.append({
            "iteration": len(history) + 1,
            "variable": columns[max_index],
            "vif": max_vif,
            "n_features": len(columns),
        })
        if np.isfinite(max_vif) and max_vif <= threshold:
            break
        columns.pop(max_index)

    return columns, pd.DataFrame(history)


def spatial_group_ids(
    longitude: Sequence[float],
    latitude: Sequence[float],
    block_size_degrees: float,
) -> np.ndarray:
    """Create rectangular spatial group IDs for leakage resistant validation."""

    if block_size_degrees <= 0:
        raise ValueError("Spatial block size must be positive")
    lon = np.asarray(longitude, dtype=float)
    lat = np.asarray(latitude, dtype=float)
    if lon.shape != lat.shape:
        raise ValueError("Longitude and latitude arrays must have the same shape")
    gx = np.floor(lon / block_size_degrees).astype(np.int64)
    gy = np.floor(lat / block_size_degrees).astype(np.int64)
    return np.asarray([f"{x}_{y}" for x, y in zip(gx, gy, strict=True)], dtype=object)


def regression_metrics(y_true: Sequence[float], y_pred: Sequence[float]) -> dict[str, float]:
    observed = np.asarray(y_true, dtype=float)
    predicted = np.asarray(y_pred, dtype=float)
    rmse = float(np.sqrt(mean_squared_error(observed, predicted)))
    iqr = float(np.subtract(*np.nanpercentile(observed, [75, 25])))
    return {
        "r_squared": float(r2_score(observed, predicted)),
        "rmse": rmse,
        "rpiq": iqr / rmse if rmse > 0.0 else float("inf"),
        "bias": float(np.mean(predicted - observed)),
    }


def prediction_interval_coverage(
    y_true: Sequence[float],
    lower: Sequence[float],
    upper: Sequence[float],
) -> float:
    observed = np.asarray(y_true, dtype=float)
    low = np.asarray(lower, dtype=float)
    high = np.asarray(upper, dtype=float)
    return float(np.mean((observed >= low) & (observed <= high)))


@dataclass
class FoldResult:
    fold: int
    metrics: dict[str, float]
    selected_features: tuple[str, ...]
    best_params: dict[str, float | int]


def _load_qrf_class():
    try:
        from quantile_forest import RandomForestQuantileRegressor
    except ImportError as exc:
        raise ImportError("Digital SOC QRF training requires quantile-forest") from exc
    return RandomForestQuantileRegressor


def nested_spatial_qrf_cv(
    features: pd.DataFrame,
    target: Sequence[float],
    groups: Sequence[str],
    config: QRFWorkflowConfig = QRFWorkflowConfig(),
    param_grid: dict[str, list[float | int]] | None = None,
) -> list[FoldResult]:
    """Run nested spatial CV, RFECV, grid tuning, and QRF uncertainty validation."""

    qrf_class = _load_qrf_class()
    x = features.select_dtypes(include=[np.number]).copy()
    x = x.replace([np.inf, -np.inf], np.nan)
    y = np.asarray(target, dtype=float)
    group_array = np.asarray(groups, dtype=object)
    if len(x) != len(y) or len(y) != len(group_array):
        raise ValueError("Features, target, and groups must have the same row count")

    outer_splits = min(config.outer_cv, int(pd.Series(group_array).nunique()))
    if outer_splits < 2:
        raise ValueError("At least two spatial groups are required")
    outer_cv = GroupKFold(n_splits=outer_splits)
    results = []
    grid = param_grid or DEFAULT_PARAM_GRID

    for fold_number, (train_index, test_index) in enumerate(
        outer_cv.split(x, y, groups=group_array), start=1
    ):
        x_train = x.iloc[train_index].copy()
        x_test = x.iloc[test_index].copy()
        y_train = y[train_index]
        y_test = y[test_index]
        train_groups = group_array[train_index]

        medians = x_train.median(numeric_only=True)
        x_train = x_train.fillna(medians)
        x_test = x_test.fillna(medians)

        scaler = StandardScaler() if config.scale_numeric_features else None
        if scaler is not None:
            x_train_values = scaler.fit_transform(x_train)
            x_test_values = scaler.transform(x_test)
        else:
            x_train_values = x_train.to_numpy(dtype=float)
            x_test_values = x_test.to_numpy(dtype=float)

        inner_splits = min(config.inner_cv, int(pd.Series(train_groups).nunique()))
        if inner_splits < 2:
            raise ValueError("Each outer training split needs at least two spatial groups")
        inner_cv = GroupKFold(n_splits=inner_splits)

        minimum_features = max(
            config.rfecv_min_absolute,
            int(np.ceil(config.rfecv_min_fraction * x_train.shape[1])),
        )
        minimum_features = min(minimum_features, x_train.shape[1])

        selector = RFECV(
            estimator=RandomForestRegressor(
                n_estimators=200,
                random_state=config.random_state,
                n_jobs=-1,
            ),
            step=config.rfecv_step,
            min_features_to_select=minimum_features,
            cv=inner_cv,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1,
        )
        selector.fit(x_train_values, y_train, groups=train_groups)
        selected_names = tuple(x_train.columns[selector.support_])
        selected_train = x_train_values[:, selector.support_]
        selected_test = x_test_values[:, selector.support_]

        tuner = GridSearchCV(
            RandomForestRegressor(random_state=config.random_state, n_jobs=-1),
            param_grid=grid,
            cv=inner_cv,
            scoring="neg_root_mean_squared_error",
            n_jobs=-1,
        )
        tuner.fit(selected_train, y_train, groups=train_groups)
        best_params = dict(tuner.best_params_)

        qrf = qrf_class(random_state=config.random_state, n_jobs=-1, **best_params)
        qrf.fit(selected_train, y_train)
        mean_prediction = np.asarray(qrf.predict(selected_test), dtype=float)
        q05 = np.asarray(qrf.predict(selected_test, quantiles=0.05), dtype=float)
        q95 = np.asarray(qrf.predict(selected_test, quantiles=0.95), dtype=float)
        metrics = regression_metrics(y_test, mean_prediction)
        metrics["picp_90"] = prediction_interval_coverage(y_test, q05, q95)
        metrics["mean_pi_width_90"] = float(np.mean(q95 - q05))

        results.append(
            FoldResult(
                fold=fold_number,
                metrics=metrics,
                selected_features=selected_names,
                best_params=best_params,
            )
        )

    return results
