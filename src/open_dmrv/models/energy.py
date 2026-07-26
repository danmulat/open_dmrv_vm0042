"""Farm fossil energy carbon dioxide emissions."""


def farm_energy_co2e(area_ha: float, diesel_l_ha: float, gasoline_l_ha: float, diesel_ef_kg_co2_l: float = 2.68, gasoline_ef_kg_co2_l: float = 2.31) -> float:
    return area_ha * (diesel_l_ha * diesel_ef_kg_co2_l + gasoline_l_ha * gasoline_ef_kg_co2_l) / 1000.0
