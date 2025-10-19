from real_estate_roi.core.scenarios import build_owner_cashflows, build_rental_cashflows
from real_estate_roi.core.model import InvestmentInputs

def test_scenarios_builders_return_dicts():
    inputs = InvestmentInputs()
    owner = build_owner_cashflows(inputs)
    rental = build_rental_cashflows(inputs)
    assert isinstance(owner, dict)
    assert isinstance(rental, dict)


