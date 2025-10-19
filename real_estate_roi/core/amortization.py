from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd


MONTHS_IN_YEAR: Final[int] = 12


def _fixed_monthly_payment(principal: float, annual_rate: float, years: int) -> float:
    """Compute the fixed monthly payment for a fully amortizing loan.

    Parameters
    ----------
    principal : float
        Initial loan amount.
    annual_rate : float
        Nominal annual interest rate as a decimal (e.g., 0.04 for 4%).
    years : int
        Loan term in years.

    Returns
    -------
    float
        The constant monthly payment.
    """
    n_months = years * MONTHS_IN_YEAR
    if principal <= 0 or n_months <= 0:
        return 0.0
    monthly_rate = annual_rate / MONTHS_IN_YEAR
    if monthly_rate == 0:
        return principal / n_months
    factor = (1 + monthly_rate) ** n_months
    return principal * (monthly_rate * factor) / (factor - 1)


def amort_schedule(principal: float, annual_rate: float, years: int) -> pd.DataFrame:
    """Generate a monthly amortization schedule.

    Columns: month (1..N), payment, interest, principal, balance

    Notes
    -----
    - Handles rounding on the last period to end with zero balance.
    - Payment is constant (except for final rounding adjustment if needed).
    """
    n_months = years * MONTHS_IN_YEAR
    payment = _fixed_monthly_payment(principal, annual_rate, years)
    monthly_rate = annual_rate / MONTHS_IN_YEAR

    if n_months == 0:
        return pd.DataFrame(
            columns=["month", "payment", "interest", "principal", "balance"],
            data=[],
        )

    rows = []
    balance = float(principal)
    for m in range(1, n_months + 1):
        interest = balance * monthly_rate
        principal_component = payment - interest

        # Guard against negative principal component due to extreme rates
        if principal_component < 0:
            principal_component = 0.0

        new_balance = balance - principal_component

        # Final adjustment to avoid tiny negative balances from rounding
        if m == n_months and abs(new_balance) < 1e-6:
            principal_component += new_balance
            payment = interest + principal_component
            new_balance = 0.0

        rows.append(
            {
                "month": m,
                "payment": float(payment),
                "interest": float(interest),
                "principal": float(principal_component),
                "balance": float(max(new_balance, 0.0)),
            }
        )
        balance = max(new_balance, 0.0)

    return pd.DataFrame(rows)


def aggregate_yearly(schedule: pd.DataFrame) -> pd.DataFrame:
    """Aggregate a monthly amortization schedule by year.

    Returns a DataFrame with columns: year, payment, interest, principal, end_balance
    """
    if schedule.empty:
        return pd.DataFrame(
            columns=["year", "payment", "interest", "principal", "end_balance"],
            data=[],
        )

    schedule = schedule.copy()
    schedule["year"] = (schedule["month"] - 1) // MONTHS_IN_YEAR + 1
    agg = (
        schedule.groupby("year", as_index=False)[["payment", "interest", "principal"]]
        .sum()
        .sort_values("year")
    )
    # Capture ending balance per year
    end_balances = (
        schedule.groupby("year", as_index=False)["balance"].last().rename(columns={"balance": "end_balance"})
    )
    return agg.merge(end_balances, on="year", how="left")


@dataclass(frozen=True)
class AmortizationSummary:
    payment_monthly: float
    schedule_monthly: pd.DataFrame
    schedule_yearly: pd.DataFrame


def summarize(principal: float, annual_rate: float, years: int) -> AmortizationSummary:
    """Convenience wrapper returning payment and schedules."""
    schedule = amort_schedule(principal, annual_rate, years)
    yearly = aggregate_yearly(schedule)
    payment = _fixed_monthly_payment(principal, annual_rate, years)
    return AmortizationSummary(payment_monthly=payment, schedule_monthly=schedule, schedule_yearly=yearly)
