"""Measured soil organic carbon stock calculations."""


def soc_stock_t_c_ha(soc_g_kg: float, bulk_density_g_cm3: float, depth_top_cm: float, depth_bottom_cm: float, coarse_fragment_percent: float = 0.0) -> float:
    if soc_g_kg < 0:
        raise ValueError("SOC concentration cannot be negative")
    if bulk_density_g_cm3 <= 0:
        raise ValueError("Bulk density must be positive")
    if depth_bottom_cm <= depth_top_cm:
        raise ValueError("Depth bottom must be greater than depth top")
    if not 0 <= coarse_fragment_percent < 100:
        raise ValueError("Coarse fragment percent must be between 0 and 100")
    thickness_cm = depth_bottom_cm - depth_top_cm
    fine_fraction = 1.0 - coarse_fragment_percent / 100.0
    return soc_g_kg * bulk_density_g_cm3 * thickness_cm * 0.1 * fine_fraction
