from open_dmrv.models.gleam_adapter import GleamEmissionBundle
from open_dmrv.whole_farm import (
    CarbonStockChange,
    FarmGHGInventory,
    FarmScenarioResult,
    ScenarioComparison,
)


def test_whole_farm_scenario_comparison() -> None:
    baseline = FarmScenarioResult(
        "baseline",
        FarmGHGInventory(GleamEmissionBundle(10, 2, 1, 3), soil_n2o_co2e_t=4),
        CarbonStockChange(soil_co2e_t=1),
    )
    intervention = FarmScenarioResult(
        "intervention",
        FarmGHGInventory(GleamEmissionBundle(8, 1, 0.8, 2.5), soil_n2o_co2e_t=3),
        CarbonStockChange(soil_co2e_t=2),
    )
    comparison = ScenarioComparison(baseline, intervention)
    assert comparison.total_climate_benefit_co2e_t > 0
