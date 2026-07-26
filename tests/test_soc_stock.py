from open_dmrv.models.soc_stock import soc_stock_t_c_ha


def test_soc_stock_calculation() -> None:
    value = soc_stock_t_c_ha(20.0, 1.2, 0.0, 15.0, 5.0)
    assert round(value, 3) == 34.2
