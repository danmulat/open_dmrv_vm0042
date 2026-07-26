"""Soil nitrous oxide accounting."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SoilN2OResult:
    direct_co2e_t: float
    indirect_co2e_t: float

    @property
    def total_co2e_t(self) -> float:
        return self.direct_co2e_t + self.indirect_co2e_t


def soil_n2o_emissions(area_ha: float, mineral_n_kg_ha: float, organic_n_kg_ha: float, residue_n_kg_ha: float, grazing_n_kg_ha: float, ef1_kg_n2on_kg_n: float, gwp_n2o: float = 273.0, indirect_fraction_of_direct: float = 0.15) -> SoilN2OResult:
    total_n = mineral_n_kg_ha + organic_n_kg_ha + residue_n_kg_ha + grazing_n_kg_ha
    direct_n2o_t = area_ha * total_n * ef1_kg_n2on_kg_n * 44.0 / 28.0 / 1000.0
    direct = direct_n2o_t * gwp_n2o
    return SoilN2OResult(direct, direct * indirect_fraction_of_direct)
