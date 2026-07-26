"""IPCC Tier 2 style enteric methane equations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EntericResult:
    emission_factor_kg_ch4_head_year: float
    methane_t: float
    co2e_t: float


def enteric_methane(head_count: float, dmi_kg_day: float, feed_gross_energy_mj_kg_dm: float, methane_conversion_factor_percent: float, gwp_ch4: float = 27.2, methane_energy_mj_kg: float = 55.65) -> EntericResult:
    ef = dmi_kg_day * feed_gross_energy_mj_kg_dm * methane_conversion_factor_percent / 100.0 * 365.0 / methane_energy_mj_kg
    methane_t = head_count * ef / 1000.0
    return EntericResult(ef, methane_t, methane_t * gwp_ch4)
