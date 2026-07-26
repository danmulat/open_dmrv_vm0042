"""Manure methane and direct nitrous oxide equations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ManureResult:
    methane_co2e_t: float
    direct_n2o_co2e_t: float

    @property
    def total_co2e_t(self) -> float:
        return self.methane_co2e_t + self.direct_n2o_co2e_t


def manure_emissions(head_count: float, volatile_solids_kg_day: float, bo_m3_ch4_kg_vs: float, methane_conversion_factor_percent: float, system_fraction_percent: float, nitrogen_excretion_kg_n_day: float, ef3_kg_n2on_kg_n: float, gwp_ch4: float = 27.2, gwp_n2o: float = 273.0, methane_density_kg_m3: float = 0.67) -> ManureResult:
    mcf = methane_conversion_factor_percent / 100.0
    fraction = system_fraction_percent / 100.0
    methane_t = head_count * volatile_solids_kg_day * 365.0 * bo_m3_ch4_kg_vs * methane_density_kg_m3 * mcf * fraction / 1000.0
    n2o_t = head_count * nitrogen_excretion_kg_n_day * 365.0 * fraction * ef3_kg_n2on_kg_n * 44.0 / 28.0 / 1000.0
    return ManureResult(methane_t * gwp_ch4, n2o_t * gwp_n2o)
