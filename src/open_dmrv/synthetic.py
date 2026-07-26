"""Reproducible Ethiopian like synthetic datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from .models.soc_stock import soc_stock_t_c_ha


@dataclass(frozen=True)
class SyntheticStratum:
    stratum_id: str
    name: str
    soil_group: str
    area_ha: float
    latitude: float
    longitude: float
    top_soc_g_kg: float
    bottom_soc_g_kg: float
    top_bulk_density: float
    bottom_bulk_density: float
    coarse_fragment_percent: float
    baseline_soc_rate_t_c_ha_year: float
    project_soc_rate_t_c_ha_year: float


STRATA = (
    SyntheticStratum("STR01", "Central highland Nitisol mixed crop dairy", "Nitisol", 500.0, 8.55, 39.25, 22.5, 14.5, 1.08, 1.18, 5.0, -0.10, 0.55),
    SyntheticStratum("STR02", "Mid altitude Vertisol crop livestock", "Vertisol", 700.0, 7.60, 38.70, 16.0, 10.5, 1.17, 1.27, 3.0, -0.12, 0.40),
    SyntheticStratum("STR03", "Lower altitude Cambisol pasture crop livestock", "Cambisol", 800.0, 6.20, 37.60, 9.5, 6.5, 1.25, 1.35, 8.0, -0.05, 0.28),
)


def generate_soc_measurements(seed: int = 20260726) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict[str, object]] = []
    start = date(2026, 6, 10)
    for stratum in STRATA:
        for site_number in range(1, 11):
            unit_id = f"{stratum.stratum_id}_F{site_number:02d}"
            set_type = "Calibration" if site_number <= 6 else "Independent_Validation" if site_number <= 8 else "Holdout" if site_number == 9 else "Monitoring"
            latitude = stratum.latitude + rng.uniform(-0.18, 0.18)
            longitude = stratum.longitude + rng.uniform(-0.18, 0.18)
            for layer, top, bottom, soc_mean, bulk_density_mean in ((1, 0.0, 15.0, stratum.top_soc_g_kg, stratum.top_bulk_density), (2, 15.0, 30.0, stratum.bottom_soc_g_kg, stratum.bottom_bulk_density)):
                soc = max(2.0, rng.normal(soc_mean, soc_mean * 0.10))
                bulk_density = float(np.clip(rng.normal(bulk_density_mean, 0.035), 0.95, 1.55))
                coarse = float(np.clip(rng.normal(stratum.coarse_fragment_percent, 1.5), 0.0, 20.0))
                rows.append({"sample_id": f"{unit_id}_D{layer}", "stratum_id": stratum.stratum_id, "unit_id": unit_id, "sample_date": start + timedelta(days=site_number), "latitude": latitude, "longitude": longitude, "depth_top_cm": top, "depth_bottom_cm": bottom, "soc_g_kg": soc, "bulk_density_g_cm3": bulk_density, "coarse_fragment_percent": coarse, "soc_stock_t_c_ha": soc_stock_t_c_ha(soc, bulk_density, top, bottom, coarse), "set_type": set_type, "qa_status": "PASS"})
    return pd.DataFrame(rows)


def site_soc_stocks(measurements: pd.DataFrame) -> pd.DataFrame:
    return measurements.groupby(["stratum_id", "unit_id", "set_type"], as_index=False).agg(observed_soc_t_c_ha=("soc_stock_t_c_ha", "sum")).sort_values(["stratum_id", "unit_id"])


def synthetic_validation(site_stocks: pd.DataFrame) -> pd.DataFrame:
    selected = site_stocks[site_stocks["set_type"].isin(["Independent_Validation", "Holdout"])].copy()
    errors = np.array([2.6, -3.2, 2.07, -2.5, 3.6, -2.185, 4.1, -3.7, 2.53])
    selected["predicted_soc_t_c_ha"] = selected["observed_soc_t_c_ha"].to_numpy() + errors
    selected["residual_t_c_ha"] = selected["predicted_soc_t_c_ha"] - selected["observed_soc_t_c_ha"]
    selected["prediction_se_t_c_ha"] = selected["stratum_id"].map({"STR01": 3.8, "STR02": 3.4, "STR03": 3.0})
    selected["covered_90_percent"] = selected["residual_t_c_ha"].abs() <= 1.645 * selected["prediction_se_t_c_ha"]
    return selected


def save_synthetic_data(directory: str | Path, seed: int = 20260726) -> dict[str, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    measurements = generate_soc_measurements(seed)
    sites = site_soc_stocks(measurements)
    validation = synthetic_validation(sites)
    paths = {"measurements": directory / "soc_measurements.csv", "site_stocks": directory / "soc_site_stocks.csv", "validation": directory / "soc_validation.csv"}
    measurements.to_csv(paths["measurements"], index=False)
    sites.to_csv(paths["site_stocks"], index=False)
    validation.to_csv(paths["validation"], index=False)
    return paths
