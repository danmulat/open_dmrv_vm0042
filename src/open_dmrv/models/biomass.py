"""Woody biomass carbon stock calculations."""


def woody_biomass_stock_co2e(aboveground_biomass_t_dm_ha: float, root_shoot_ratio: float = 0.24, carbon_fraction: float = 0.47) -> float:
    carbon_t_ha = aboveground_biomass_t_dm_ha * (1.0 + root_shoot_ratio) * carbon_fraction
    return carbon_t_ha * 44.0 / 12.0
