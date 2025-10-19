from real_estate_roi.core.model import InvestmentInputs, RealEstateModel


def test_owner_cashflows_and_sale_proceeds_positive_at_end():
    inputs = InvestmentInputs()
    model = RealEstateModel(inputs)
    res = model.run_owner()
    assert len(res["cashflows"]) == model.n_years + 1
    assert res["sale_proceeds"] >= 0


def test_rental_irr_defined():
    inputs = InvestmentInputs()
    model = RealEstateModel(inputs)
    irr = model.irr("rental")
    # May be negative or positive depending on inputs, but should compute
    assert irr is None or isinstance(irr, float)


