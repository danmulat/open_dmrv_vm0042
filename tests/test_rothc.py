from open_dmrv.models.rothc import RothCInputs, run_scenarios_from_same_initial


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
