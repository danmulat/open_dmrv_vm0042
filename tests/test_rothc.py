import pytest

from open_dmrv.models.rothc import (
    RothCInputs,
    RothCModel,
    RothCPools,
    run_scenarios_from_same_initial,
)


def _official_equilibrium_inputs() -> RothCInputs:
    return RothCInputs(
        temperatures_c=(
            3.73,
            3.08,
            5.49,
            7.40,
            10.94,
            14.40,
            16.28,
            16.24,
            13.78,
            9.51,
            6.22,
            4.09,
        ),
        rainfall_mm=(
            52.2,
            42.9,
            35.2,
            52.0,
            64.9,
            46.3,
            63.5,
            60.6,
            58.8,
            63.4,
            72.5,
            60.9,
        ),
        pet_mm=(
            6.6,
            17.3,
            40.7,
            70.5,
            103.5,
            117.3,
            130.1,
            106.9,
            61.9,
            29.5,
            8.8,
            3.9,
        ),
        clay_percent=13.0,
        depth_cm=25.0,
        annual_plant_c_t_ha=1.74,
        annual_manure_c_t_ha=0.0,
        dpm_rpm_ratio=1.44,
        soil_cover=(True, True, True, True, True, True, True, True, False, True, True, True),
        monthly_plant_c_t_ha=(0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.74, 0.0, 0.0, 0.0, 0.0),
    )


def test_same_initial_soc() -> None:
    inputs = RothCInputs(
        temperatures_c=(18.0,) * 12,
        rainfall_mm=(100.0,) * 12,
        pet_mm=(80.0,) * 12,
        clay_percent=35.0,
        annual_plant_c_t_ha=3.0,
        annual_manure_c_t_ha=0.5,
        dpm_rpm_ratio=1.2,
        soil_cover=(True,) * 12,
    )
    baseline, project = run_scenarios_from_same_initial(50.0, inputs, inputs, 2)
    assert baseline[0] == project[0] == 50.0
    assert baseline == project


def test_official_rothc_equilibrium_benchmark() -> None:
    inputs = _official_equilibrium_inputs()
    model = RothCModel(
        clay_percent=13.0,
        depth_cm=25.0,
        pools=RothCPools(iom=3.0041),
    )
    model.spin_up(inputs)

    assert model.pools.dpm == pytest.approx(0.14546618698414296, abs=1e-9)
    assert model.pools.rpm == pytest.approx(5.678120858752452, abs=1e-9)
    assert model.pools.bio == pytest.approx(0.7405937979752077, abs=1e-9)
    assert model.pools.hum == pytest.approx(27.642769420831222, abs=1e-9)
    assert model.pools.iom == pytest.approx(3.0041, abs=1e-12)
    assert model.pools.total == pytest.approx(37.211050264543026, abs=1e-9)


def test_monthly_results_preserve_pool_sum() -> None:
    inputs = _official_equilibrium_inputs()
    model = RothCModel(
        clay_percent=13.0,
        depth_cm=25.0,
        pools=RothCPools(iom=3.0041),
    )
    result = model.run_monthly(inputs, 1)
    assert len(result) == 12
    assert result[-1].soc_t_c_ha == pytest.approx(model.pools.total)


def test_model_rejects_mismatched_soil_properties() -> None:
    inputs = _official_equilibrium_inputs()
    model = RothCModel(40.0, clay_percent=30.0, depth_cm=25.0)
    with pytest.raises(ValueError, match="clay and depth"):
        model.step_month(inputs, 0)
