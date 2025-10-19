from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from .amortization import summarize as amort_summarize
from .amortization import aggregate_yearly
from .taxes import rental_effective_tax, capital_gains_tax
from .utils import irr as irr_fn, npv as npv_fn, grow, years_between
from .utils import future_value_with_monthly_withdrawals


@dataclass
class InvestmentInputs:
    # Purchase & costs
    price: float = 250_000.0
    notary_pct: float = 0.075
    agency_pct: float = 0.03
    renovation_costs: float = 10_000.0
    extra_fees: float = 2_000.0

    # Loan
    loan_rate: float = 0.04
    loan_years: int = 25
    down_payment: float = 50_000.0

    # Recurring costs
    property_tax_annual: float = 1_200.0
    other_taxes_annual: float = 0.0
    insurance_rate_on_initial_per_year: float = 0.0025  # 0.25%
    copro_charges_annual: float = 1_200.0
    copro_growth_rate: float = 0.02
    maintenance_rate_of_value: float = 0.01

    # Growth & timeline
    benchmark_return_rate: float = 0.05
    price_growth_rate: float = 0.02
    inflation_rate: float = 0.02
    purchase_year: int = 2026
    sale_year: int = 2036

    # Rental specific
    occupancy_rate: float = 0.92
    rent_monthly: float = 1_100.0
    rent_growth_rate: float = 0.02
    management_fee_rate: float = 0.06
    rental_tax_rate: float = 0.30

    # Exit costs/taxes
    selling_fees_rate: float = 0.05
    capital_gains_eff_rate: float = 0.0  # 0% for RP by default
    include_early_repayment_penalty: bool = False
    benchmark_rent_monthly: float = 800.0
    # Discounting
    discount_rate: float = 0.02


class RealEstateModel:
    def __init__(self, inputs: InvestmentInputs):
        self.inputs = inputs

        # Compute loan principal as price + all initial costs - down payment
        self.initial_costs = self._initial_costs()
        self.loan_principal_value = max(
            0.0, self.inputs.price + self.initial_costs - self.inputs.down_payment
        )

        self.amort = amort_summarize(
            principal=self.loan_principal_value,
            annual_rate=self.inputs.loan_rate,
            years=self.inputs.loan_years,
        )
        self.amort_yearly = aggregate_yearly(self.amort.schedule_monthly)

        self.n_years = years_between(self.inputs.purchase_year, self.inputs.sale_year)
        self.years = list(range(1, self.n_years + 1))

    # ------------------------- Core calculators ------------------------- #
    def _initial_costs(self) -> float:
        return (
            self.inputs.notary_pct * self.inputs.price
            + self.inputs.agency_pct * self.inputs.price
            + self.inputs.renovation_costs
            + self.inputs.extra_fees
        )

    def _annual_insurance(self) -> float:
        return self.inputs.insurance_rate_on_initial_per_year * self.loan_principal_value

    def _property_value_at(self, year_index: int) -> float:
        # year_index: 1..N
        return grow(self.inputs.price, self.inputs.price_growth_rate, year_index)

    def _maintenance_cost(self, year_index: int) -> float:
        return self.inputs.maintenance_rate_of_value * self._property_value_at(year_index)

    def _copro_charges(self, year_index: int) -> float:
        return grow(
            self.inputs.copro_charges_annual, self.inputs.copro_growth_rate, year_index - 1
        )

    def _rental_revenue_gross(self, year_index: int) -> float:
        base = self.inputs.rent_monthly * 12.0 * self.inputs.occupancy_rate
        return grow(base, self.inputs.rent_growth_rate, year_index - 1)

    def _rental_net_after_tax_before_debt(self, year_index: int) -> float:
        rent = self._rental_revenue_gross(year_index)
        mgmt = self.inputs.management_fee_rate * rent
        charges = (
            self.inputs.property_tax_annual
            + self.inputs.other_taxes_annual
            + self._copro_charges(year_index)
            + self._maintenance_cost(year_index)
            + self._annual_insurance()
        )
        net_before_tax = rent - mgmt - charges
        tax = rental_effective_tax(net_before_tax, self.inputs.rental_tax_rate)
        return net_before_tax - tax

    def sale_proceeds(self, year_index: int) -> float:
        # Sale occurs at end of year_index
        sale_price = self._property_value_at(year_index)
        selling_fees = self.inputs.selling_fees_rate * sale_price
        # Outstanding balance at end of that year:
        try:
            end_balance = float(
                self.amort_yearly.loc[self.amort_yearly["year"] == year_index, "end_balance"].values[0]
            )
        except IndexError:
            end_balance = 0.0

        gain = max(0.0, sale_price - self.inputs.price)
        tax_pv = capital_gains_tax(gain, self.inputs.capital_gains_eff_rate)
        # Early repayment penalty (IRA - Indemnité remboursement anticipé) if applicable
        ira = 0.0
        if self.inputs.include_early_repayment_penalty and end_balance > 0:
            six_month_interest = 0.5 * self.inputs.loan_rate * end_balance
            three_percent_cap = 0.03 * end_balance
            ira = min(six_month_interest, three_percent_cap)

        return sale_price - selling_fees - end_balance - tax_pv - ira

    # ------------------------- Scenarios ------------------------- #
    def run_owner(self) -> Dict[str, object]:
        # CF0: down payment as initial outflow
        cashflows: List[float] = [-self.inputs.down_payment]
        rows = []

        for y in self.years:
            loan_payments = float(
                self.amort_yearly.loc[self.amort_yearly["year"] == y, "payment"].values[0]
            ) if y <= len(self.amort_yearly) else 0.0

            charges = (
                self.inputs.property_tax_annual
                + self.inputs.other_taxes_annual
                + self._copro_charges(y)
                + self._maintenance_cost(y)
                + self._annual_insurance()
            )

            cf = -loan_payments - charges
            sale_p = 0.0
            if y == self.n_years:
                sale_p = self.sale_proceeds(y)
                cf += sale_p
            cashflows.append(cf)

            # Net worth tracking
            end_balance = float(
                self.amort_yearly.loc[self.amort_yearly["year"] == y, "end_balance"].values[0]
            ) if y <= len(self.amort_yearly) else 0.0
            prop_val = self._property_value_at(y)
            cum_cash = sum(cashflows)
            net_worth = prop_val - end_balance + cum_cash

            rows.append(
                {
                    "year": y,
                    "loan_payment": float(loan_payments),
                    "charges": float(charges),
                    "sale_proceeds": float(sale_p),
                    "cashflow": cf,
                    "cumulative_cash": cum_cash,
                    "property_value": prop_val,
                    "outstanding_balance": end_balance,
                    "net_worth": net_worth,
                }
            )

        df = pd.DataFrame(rows)
        res = {
            "cashflows": cashflows,
            "yearly": df,
            "irr": irr_fn(cashflows),
            "npv": npv_fn(self.inputs.discount_rate, cashflows),
            "monthly_payment": self.amort.payment_monthly,
            "sale_proceeds": self.sale_proceeds(self.n_years) if self.n_years > 0 else 0.0,
        }
        return res

    def run_rental(self) -> Dict[str, object]:
        cashflows: List[float] = [-self.inputs.down_payment]
        rows = []

        for y in self.years:
            loan_payments = float(
                self.amort_yearly.loc[self.amort_yearly["year"] == y, "payment"].values[0]
            ) if y <= len(self.amort_yearly) else 0.0

            # Compute charges breakdown for rental
            rent = self._rental_revenue_gross(y)
            mgmt = self.inputs.management_fee_rate * rent
            base_charges = (
                self.inputs.property_tax_annual
                + self.inputs.other_taxes_annual
                + self._copro_charges(y)
                + self._maintenance_cost(y)
                + self._annual_insurance()
            )
            net_before_tax = rent - mgmt - base_charges
            tax = rental_effective_tax(net_before_tax, self.inputs.rental_tax_rate)
            charges_total = mgmt + base_charges + tax

            net_operating = rent - charges_total
            cf = net_operating - loan_payments
            sale_p = 0.0
            if y == self.n_years:
                sale_p = self.sale_proceeds(y)
                cf += sale_p
            cashflows.append(cf)

            end_balance = float(
                self.amort_yearly.loc[self.amort_yearly["year"] == y, "end_balance"].values[0]
            ) if y <= len(self.amort_yearly) else 0.0
            prop_val = self._property_value_at(y)
            cum_cash = sum(cashflows)
            net_worth = prop_val - end_balance + cum_cash

            rows.append(
                {
                    "year": y,
                    "loan_payment": float(loan_payments),
                    "cashflow": cf,
                    "operating_before_debt": net_operating,
                    "charges": float(charges_total),
                    "sale_proceeds": float(sale_p),
                    "cumulative_cash": cum_cash,
                    "property_value": prop_val,
                    "outstanding_balance": end_balance,
                    "net_worth": net_worth,
                    "rent_gross": self._rental_revenue_gross(y),
                }
            )

        df = pd.DataFrame(rows)
        res = {
            "cashflows": cashflows,
            "yearly": df,
            "irr": irr_fn(cashflows),
            "npv": npv_fn(self.inputs.discount_rate, cashflows),
            "monthly_payment": self.amort.payment_monthly,
            "sale_proceeds": self.sale_proceeds(self.n_years) if self.n_years > 0 else 0.0,
        }
        return res

    def benchmark_apport(self) -> float:
        months = self.n_years * 12
        return future_value_with_monthly_withdrawals(
            down_payment=self.inputs.down_payment,
            annual_rate=self.inputs.benchmark_return_rate,
            monthly_payment=max(0.0, float(self.inputs.benchmark_rent_monthly)),
            months=months,
        )

    # Convenience
    def irr(self, scenario: str = "owner") -> Optional[float]:
        if scenario == "owner":
            return irr_fn(self.run_owner()["cashflows"])  # type: ignore[index]
        if scenario == "rental":
            return irr_fn(self.run_rental()["cashflows"])  # type: ignore[index]
        return None

    def npv(self, discount_rate: Optional[float] = None, scenario: str = "owner") -> Optional[float]:
        rate = self.inputs.discount_rate if discount_rate is None else float(discount_rate)
        if scenario == "owner":
            return npv_fn(rate, self.run_owner()["cashflows"])  # type: ignore[index]
        if scenario == "rental":
            return npv_fn(rate, self.run_rental()["cashflows"])  # type: ignore[index]
        return None


