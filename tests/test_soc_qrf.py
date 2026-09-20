import numpy as np
import pandas as pd

from open_dmrv.models.soc_qrf import (
    QRFWorkflowConfig,
    compute_common_ts_features,
    correlation_cluster_select,
    prediction_interval_coverage,
    spatial_group_ids,
    vif_filter,
)


def test_vm0042_depth_floor_in_qrf_config() -> None:
    config = QRFWorkflowConfig(minimum_soc_depth_cm=30.0)
    assert config.minimum_soc_depth_cm == 30.0


def test_time_series_features_have_expected_reference_keys() -> None:
    values = np.tile(np.arange(1.0, 13.0), 3)
    features = compute_common_ts_features(values)
    assert features["mean"] == 6.5
    assert "fourier2_phase_rad" in features
    assert "autocorr_lag12" in features


def test_spatial_group_ids_are_stable() -> None:
    groups = spatial_group_ids([35.00, 35.01], [0.10, 0.11], 0.05)
    assert groups.shape == (2,)
    assert all(isinstance(value, str) for value in groups)


def test_feature_filters_return_columns() -> None:
    frame = pd.DataFrame(
        {
            "a": np.arange(1.0, 21.0),
            "b": np.arange(1.0, 21.0) * 2.0,
            "c": np.sin(np.arange(1.0, 21.0)),
        }
    )
    representatives, assignment = correlation_cluster_select(frame)
    assert representatives
    assert set(assignment.columns) == {"variable", "cluster"}
    kept, _ = vif_filter(frame[representatives], threshold=10.0)
    assert kept


def test_prediction_interval_coverage() -> None:
    coverage = prediction_interval_coverage([1, 2, 3], [0, 1, 2], [2, 3, 4])
    assert coverage == 1.0
