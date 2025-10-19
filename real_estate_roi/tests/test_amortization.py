import math

from real_estate_roi.core.amortization import amort_schedule, summarize


def test_fixed_payment_known_case():
    principal = 100_000
    annual_rate = 0.05
    years = 20
    s = summarize(principal, annual_rate, years)
    # Known approximate monthly payment for 100k @5% over 20y ~ 659.96
    assert math.isclose(s.payment_monthly, 659.96, rel_tol=1e-3, abs_tol=1e-1)


def test_amort_schedule_balances_down_to_zero():
    principal = 200_000
    annual_rate = 0.04
    years = 25
    df = amort_schedule(principal, annual_rate, years)
    assert df.iloc[-1]["balance"] == 0.0


