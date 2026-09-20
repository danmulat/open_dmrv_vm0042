import pytest

from open_dmrv.models.soc_stock import (
    SoilLayer,
    aggregate_soc_layers_t_c_ha,
    validate_vm0042_depth,
)


def test_vm0042_quantification_rejects_shallow_profile() -> None:
    with pytest.raises(ValueError):
        validate_vm0042_depth(20.0)


def test_vm0042_allows_shallow_calibration_with_extrapolation_documented() -> None:
    validate_vm0042_depth(
        20.0,
        purpose="calibration_validation",
        extrapolation_method="locally validated depth function to 30 cm",
    )


def test_layer_aggregation_requires_and_reaches_30_cm() -> None:
    layers = [
        SoilLayer(20.0, 1.2, 0.0, 10.0, 5.0),
        SoilLayer(15.0, 1.3, 10.0, 30.0, 10.0),
    ]
    value = aggregate_soc_layers_t_c_ha(layers)
    assert value > 0.0


def test_layer_aggregation_rejects_gap() -> None:
    layers = [
        SoilLayer(20.0, 1.2, 0.0, 10.0, 5.0),
        SoilLayer(15.0, 1.3, 15.0, 30.0, 10.0),
    ]
    with pytest.raises(ValueError):
        aggregate_soc_layers_t_c_ha(layers)
