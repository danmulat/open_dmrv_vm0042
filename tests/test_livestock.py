from open_dmrv.models.livestock import enteric_methane


def test_enteric_methane_positive() -> None:
    result = enteric_methane(100, 8.0, 18.4, 6.5)
    assert result.emission_factor_kg_ch4_head_year > 0
    assert result.co2e_t > 0
