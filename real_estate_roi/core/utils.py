from __future__ import annotations

from typing import Iterable, Optional


def euro(value: float) -> str:
    return f"{value:,.0f} €".replace(",", " ")


def grow(value: float, annual_rate: float, years: int) -> float:
    if years <= 0:
        return value
    return value * (1 + annual_rate) ** years


def npv(rate: float, cashflows: Iterable[float]) -> float:
    """Net present value for a series of cashflows CF_t at t=0..N.

    NPV = sum(CF_t / (1 + rate)^t)
    """
    total = 0.0
    for t, cf in enumerate(cashflows):
        total += cf / ((1 + rate) ** t)
    return total


def irr(cashflows: Iterable[float], guess: float = 0.1) -> Optional[float]:
    """Compute IRR using a robust bisection method.

    Returns None if IRR cannot be bracketed.
    """
    cfs = list(cashflows)
    # Quick out: all zeros
    if all(abs(x) < 1e-12 for x in cfs):
        return None

    def npv_at(rate: float) -> float:
        return npv(rate, cfs)

    # Try to bracket the root between [low, high]
    low, high = -0.999, 10.0
    f_low = npv_at(low)
    f_high = npv_at(high)
    if f_low * f_high > 0:
        # Attempt to expand the high bound
        for high in [20.0, 50.0, 100.0]:
            f_high = npv_at(high)
            if f_low * f_high <= 0:
                break
        else:
            return None

    # Bisection
    for _ in range(200):
        mid = (low + high) / 2
        f_mid = npv_at(mid)
        if abs(f_mid) < 1e-9:
            return mid
        if f_low * f_mid <= 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return (low + high) / 2

def years_between(start_year: int, end_year: int) -> int:
    return max(0, int(end_year) - int(start_year))


def monthly_rate_from_annual(annual_rate: float) -> float:
    """Convert nominal annual rate to effective monthly rate.

    Uses compounding: r_m = (1 + r_a)^(1/12) - 1
    """
    if annual_rate <= -1.0:
        return 0.0
    return (1.0 + annual_rate) ** (1.0 / 12.0) - 1.0


def future_value_with_monthly_withdrawals(
    down_payment: float,
    annual_rate: float,
    monthly_payment: float,
    months: int,
    payment_growth_annual: float = 0.0,
) -> float:
    """Future value after monthly compounding with monthly outflows.

    - Grows capital monthly at r_m = (1+r_a)^(1/12) - 1
    - Withdraws "monthly_payment" each month
    - Optionally grows the monthly payment at a monthly growth derived
      from the provided annual growth rate (e.g. inflation)
    """
    if months <= 0:
        return float(down_payment)
    r_m = monthly_rate_from_annual(annual_rate)
    g_m = monthly_rate_from_annual(payment_growth_annual)
    value = float(down_payment)
    pay = float(monthly_payment)
    for _ in range(months):
        value = value * (1.0 + r_m) - pay
        # increase next month's payment by growth (if any)
        pay *= (1.0 + g_m)
    return value


# benchmark_annual_table has been superseded by RealEstateModel.run_financial_investment().
# Keeping the importable name for backward compatibility in case third-party code uses it.
def benchmark_annual_table(*args, **kwargs):  # type: ignore[unused-argument]
    raise NotImplementedError(
        "benchmark_annual_table moved to RealEstateModel.run_financial_investment(); "
        "use model.run_financial_investment()['annual'] and ['apport_series'] instead"
    )


