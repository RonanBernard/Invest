from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
import pandas as pd

from .amortization import summarize as amort_summarize
from .amortization import aggregate_yearly
from .taxes import rental_effective_tax, capital_gains_tax
from .utils import irr as irr_fn, npv as npv_fn, grow, years_between
from .utils import monthly_rate_from_annual

'''
v2
corrects to get equivalent cashflows : the additional cost from owner (mortgage + charges) is invested in the renting scenario.

'''

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
    # Evaluation horizon (years from purchase) for KPIs/graphs; must be >= sale horizon
    evaluation_years: int = 10
    # Financial investment taxation at evaluation date
    financial_investment_tax_rate: float = 0.0


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

        # Horizons
        self.n_sale_years = years_between(self.inputs.purchase_year, self.inputs.sale_year)
        self.n_years = max(int(self.inputs.evaluation_years), int(self.n_sale_years))
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
                self.amort_yearly.loc[self.amort_yearly["année"] == year_index, "solde_restant_du_crédit"].values[0]
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

    def early_repayment_penalty(self, year_index: int) -> float:
        """Compute IRA (early repayment penalty) at end of given year.

        Returns 0 if not included or if no outstanding balance.
        """
        try:
            end_balance = float(
                self.amort_yearly.loc[self.amort_yearly["année"] == year_index, "solde_restant_du_crédit"].values[0]
            )
        except IndexError:
            end_balance = 0.0
        if not self.inputs.include_early_repayment_penalty or end_balance <= 0:
            return 0.0
        six_month_interest = 0.5 * float(self.inputs.loan_rate) * end_balance
        three_percent_cap = 0.03 * end_balance
        return float(min(six_month_interest, three_percent_cap))

    # ------------------------- Monthly owner engine ------------------------- #
    def _buying_1_monthly(self) -> pd.DataFrame:
        """Compute authoritative monthly cashflows for the owner scenario.

        - Before sale: monthly loan payment and non-debt charges (both negative)
        - At sale month (end of sale year): add sale proceeds and seed invested value
        - After sale: pay monthly rent (negative) and grow invested value monthly
        - Final month of evaluation: add invested value to cashflow
        """
        rows: List[Dict[str, float]] = []
        cum_cash = -float(self.inputs.down_payment)
        monthly_payment = float(self.amort.payment_monthly)
        invested_value = 0.0
        invested_principal = 0.0
        r_m_invest = monthly_rate_from_annual(float(self.inputs.benchmark_return_rate))

        rows.append({
            "année": 0,
            "mois": 0,
            "mensualité": 0.0,
            "charges": 0.0,
            "loyer_évité": 0.0,
            "produit_net_de_vente": 0.0,
            "investissement": 0.0,
            "cashflows": -float(self.inputs.down_payment),
            "cashflows_cumulés": -float(self.inputs.down_payment),
            "valeur_du_bien": 0.0,
            "solde_restant_du_crédit": float(self.loan_principal_value),
            "capital_investi": 0.0,
        })

        for y in range(1, self.n_years + 1):
            # Annual non-debt charges while owned (spread evenly over months)
            charges_annual = (
                    self.inputs.property_tax_annual
                    + self.inputs.other_taxes_annual
                    + self._copro_charges(y)
                    + self._maintenance_cost(y)
                    + self._annual_insurance()
                )
            charge_monthly = float(charges_annual) / 12.0

            # Annual rent after sale (constant within the year)
            rent_avoided_annual = 12.0 * float(self.inputs.benchmark_rent_monthly) * (
                (1.0 + float(self.inputs.rent_growth_rate)) ** (y - 1)
            )
            rent_avoided_monthly = float(rent_avoided_annual) / 12.0

            for m in range(1, 12 + 1):
                global_month = (y - 1) * 12 + m
                try:
                    end_balance = float(
                        self.amort.schedule_monthly.loc[
                            self.amort.schedule_monthly["mois_global"] == global_month, "solde_restant_du_crédit"
                        ].values[0]
                    )
                except IndexError:
                    end_balance = 0.0

                loan_payment = 0.0
                charges = 0.0
                sale_p = 0.0
                prop_val = 0.0
                invested_value_growth = 0.0
                invested_value_tax = 0.0

                if y <= self.n_sale_years:
                    # Before sale: debt service and charges
                    # Stop loan payment after the loan term
                    loan_payment = -monthly_payment if global_month <= int(self.inputs.loan_years) * 12 else 0.0
                    charges = -charge_monthly
                    # Sale at month 12 of sale year
                    prop_val = self._property_value_at(y)
                    rent_avoided = rent_avoided_monthly
                else:
                    rent_avoided = 0

                invested_value_growth = invested_value * r_m_invest  # monthly gain only
                invested_value += invested_value_growth

                if y == self.n_sale_years and m == 12:
                    sale_p = float(self.sale_proceeds(y))
                    invested_value += float(sale_p)
                    invested_principal += float(sale_p)

                cf = loan_payment + charges + rent_avoided + sale_p - sale_p # sale_p is directly invested

                if cf > 0:
                    invested_value += cf
                    invested_principal += cf
                
                if y == self.n_years and m == 12:
                    total_gains = invested_value - invested_principal
                    total_tax = float(self.inputs.financial_investment_tax_rate) * total_gains
                    cf += total_gains - total_tax + invested_principal

                cum_cash += cf

                rows.append(
                    {
                        "année": y,
                        "mois": m,
                        "mensualité": loan_payment,
                        "charges": charges,
                        "loyer_évité": rent_avoided,
                        "produit_net_de_vente": sale_p,
                        "investissement": invested_value,
                        "cashflows": cf,
                        "cashflows_cumulés": cum_cash,
                        "valeur_du_bien": prop_val,
                        "solde_restant_du_crédit": end_balance,
                        "capital_investi": invested_principal,
                    }
                )

        return pd.DataFrame(rows)

    # ------------------------- Monthly rental engine ------------------------- #
    def _buying_2_monthly(self) -> pd.DataFrame:
        rows: List[Dict[str, float]] = []
        cum_cash = -float(self.inputs.down_payment)
        monthly_payment = float(self.amort.payment_monthly)
        invested_value = 0.0
        invested_principal = 0.0
        r_m_invest = monthly_rate_from_annual(float(self.inputs.benchmark_return_rate))

        rows.append({
            "année": 0,
            "mois": 0,
            "mensualité": 0.0,
            "charges": 0.0,
            "loyer_reçu": 0.0,
            "loyer_évité": 0.0,
            "produit_net_de_vente": 0.0,
            "investissement": 0.0,
            "cashflows": -float(self.inputs.down_payment),
            "cashflows_cumulés": -float(self.inputs.down_payment),
            "valeur_du_bien": 0.0,
            "solde_restant_du_crédit": float(self.loan_principal_value),
            "capital_investi": 0.0,
        })
        
        for y in range(1, self.n_years + 1):
            # Annual components
            rent_gross_annual = self._rental_revenue_gross(y)
            rent_gross_monthly = float(rent_gross_annual) / 12.0
            base_charges_annual = (
                    self.inputs.property_tax_annual
                    + self.inputs.other_taxes_annual
                    + self._copro_charges(y)
                    + self._maintenance_cost(y)
                    + self._annual_insurance()
                )
            base_charges_monthly = float(base_charges_annual) / 12.0
            # Personal rent monthly (same as IF rent for this year)
            rent_avoided_annual = 12.0 * float(self.inputs.benchmark_rent_monthly) * (
                (1.0 + float(self.inputs.rent_growth_rate)) ** (y - 1)
            )
            rent_avoided_monthly = float(rent_avoided_annual) / 12.0

            for m in range(1, 12 + 1):
                global_month = (y - 1) * 12 + m
                try:
                    end_balance = float(
                        self.amort.schedule_monthly.loc[
                            self.amort.schedule_monthly["mois_global"] == global_month, "solde_restant_du_crédit"
                        ].values[0]
                    )
                except IndexError:
                    end_balance = 0.0

                loan_payment = 0.0
                charges = 0.0
                sale_p = 0.0
                prop_val = 0.0
                invested_value_growth = 0.0
                invested_value_tax = 0.0

                # Before sale horizon: no rent revenues, only base charges; after sale horizon: rent and mgmt/tax
                if y <= self.n_sale_years:
                    rent_revenues = 0.0
                    mgmt_monthly = 0.0
                    tax_monthly = 0.0
                    charges_monthly = -base_charges_monthly
                    rent_avoided = rent_avoided_monthly
                else:
                    rent_revenues = rent_gross_monthly
                    mgmt_monthly = float(self.inputs.management_fee_rate) * rent_gross_monthly
                    net_before_tax_annual = float(rent_gross_annual) - mgmt_monthly - float(base_charges_annual)
                    tax_annual = rental_effective_tax(net_before_tax_annual, self.inputs.rental_tax_rate)
                    tax_monthly = float(tax_annual) / 12.0
                    charges_monthly = -(mgmt_monthly + base_charges_monthly + tax_monthly)
                    rent_avoided = 0

                invested_value_growth = invested_value * r_m_invest  # monthly gain only
                invested_value += invested_value_growth

                # Stop loan payment after the loan term
                loan_payment = -monthly_payment if global_month <= int(self.inputs.loan_years) * 12 else 0.0
                cf = loan_payment + charges_monthly + rent_revenues + rent_avoided

                if cf > 0:
                    invested_value += cf
                    invested_principal += cf

                if y == self.n_years and m == 12:
                    sale_p = float(self.sale_proceeds(y))
                    cf += sale_p
                if y == self.n_years and m == 12:
                    total_gains = invested_value - invested_principal
                    total_tax = float(self.inputs.financial_investment_tax_rate) * total_gains
                    cf += total_gains - total_tax + invested_principal

                cum_cash += cf
                prop_val = self._property_value_at(y)
                net_worth = prop_val - end_balance + cum_cash if not (y == self.n_years and m == 12) else cum_cash

                rows.append(
                {
                    "année": y,
                    "mois": m,
                    "mensualité": loan_payment,
                    "charges": charges_monthly,
                    "loyer_reçu": rent_revenues,
                    "loyer_évité": rent_avoided,
                    "produit_net_de_vente": sale_p,
                    "investissement": invested_value,
                    "cashflows": cf,
                    "cashflows_cumulés": cum_cash,
                    "valeur_du_bien": prop_val,
                    "solde_restant_du_crédit": end_balance,
                    "capital_investi": invested_principal,
                    }
                )

        return pd.DataFrame(rows)

    def _renting_monthly(self, scenario: str = "buying_1") -> pd.DataFrame:
        rows: List[Dict[str, float]] = []
        years = int(self.n_years)
        months_total = years * 12
        r_m = monthly_rate_from_annual(float(self.inputs.benchmark_return_rate))
        g_m = monthly_rate_from_annual(float(self.inputs.rent_growth_rate))
        monthly_payment = float(self.amort.payment_monthly)
        invested_value = float(self.inputs.down_payment)
        invested_principal = float(self.inputs.down_payment)
        rent_m = -float(self.inputs.benchmark_rent_monthly)
        cum_cash = -invested_value
        # Initial row (y0)
        rows.append({
            "année": 0,
            "mois": 0,
            "loyer": 0,
            "différence_flux_avec_achat": 0.0,
            "investissement": invested_value,
            "cashflows": -invested_value,
            "cashflows_cumulés": -invested_value,
            "capital_investi": invested_principal,
        })

        for y in range(1, self.n_years + 1):
            # Annual non-debt charges while owned (spread evenly over months)
            charges_annual = (
                        self.inputs.property_tax_annual
                        + self.inputs.other_taxes_annual
                        + self._copro_charges(y)
                        + self._maintenance_cost(y)
                        + self._annual_insurance()
                    )
            charge_monthly = float(charges_annual) / 12.0

            # Annual rent after sale (constant within the year)
            rent_annual = 12.0 * float(self.inputs.benchmark_rent_monthly) * (
                (1.0 + float(self.inputs.rent_growth_rate)) ** (y - 1)
            )
            rent_monthly = float(rent_annual) / 12.0
            
            for m in range(1, 12 + 1):
                global_month = (y - 1) * 12 + m
                try:
                    end_balance = float(
                        self.amort.schedule_monthly.loc[
                            self.amort.schedule_monthly["mois_global"] == global_month, "solde_restant_du_crédit"
                        ].values[0]
                    )
                except IndexError:
                    end_balance = 0.0

                loan_payment = 0.0
                charges = 0.0
                rent = -rent_monthly 
                sale_p = 0.0
                prop_val = 0.0
                invested_value_growth = 0.0
                invested_value_tax = 0.0
                rent_revenues = 0.0

                if y <= self.n_sale_years:
                    # Before sale: debt service and charges
                    try:
                        pmt = float(
                            self.amort.schedule_monthly.loc[
                                self.amort.schedule_monthly["mois_global"] == global_month, "mensualité"
                            ].values[0]
                        )
                    except IndexError:
                        pmt = 0.0
                    # Stop loan payment after loan term
                    loan_payment = monthly_payment if global_month <= int(self.inputs.loan_years) * 12 else 0.0
                    charges = charge_monthly
                    rent_buying = 0
                else:
                    if scenario == "buying_1":
                        # After sale: invested capital grows monthly; rent paid monthly
                        loan_payment = 0
                        charges = 0
                        rent_buying = rent_monthly
                    elif scenario == "buying_2":
                        # After sale: invested capital grows monthly; rent paid monthly
                        # Stop loan payment after loan term
                        loan_payment = monthly_payment if global_month <= int(self.inputs.loan_years) * 12 else 0.0
                        rent_gross_annual = self._rental_revenue_gross(y)
                        rent_gross_monthly = float(rent_gross_annual) / 12.0
                        mgmt_monthly = float(self.inputs.management_fee_rate) * rent_gross_monthly
                        charges = charge_monthly + mgmt_monthly
                        rent_revenues = -rent_gross_monthly
                        rent_buying = rent_monthly
                        
                invested_value_growth = invested_value * r_m
                invested_value += invested_value_growth

                delta_buying = (loan_payment + charges + rent_buying + rent_revenues) + rent # Expenses in buying scenario are revenues here
                
                cf = 0.0
                if delta_buying < 0:
                    cf += delta_buying
                else:
                    invested_principal += delta_buying  # invest the additional savings in the rental scenario
                    invested_value += delta_buying
                
                if y == self.n_years and m == 12:                
                    total_gains = invested_value - invested_principal
                    total_tax = float(self.inputs.financial_investment_tax_rate) * total_gains
                    cf += total_gains - total_tax + invested_principal
                cum_cash += cf
                rows.append({
                    "année": y,
                    "mois": m,
                    "loyer": rent,
                    "différence_flux_avec_achat": delta_buying,
                    "investissement": invested_value,
                    "cashflows": cf,
                    "cashflows_cumulés": cum_cash,
                    "capital_investi": invested_principal,
                })
        return pd.DataFrame(rows)

    @staticmethod
    def _aggregate_monthly_to_annual(df_m: pd.DataFrame) -> pd.DataFrame:
        """Aggregate owner monthly dataframe to annual values.

        - Sum: cashflow, loan_payment, charges, rent, sale_proceeds, operating_before_debt,
                rent_revenues, rent_personal (only those present)
        - Last-of-year: cumulative_cash, property_value, outstanding_balance, net_worth,
                invested_value_after_sale (only those present)
        """
        candidate_sum_cols = [
            "mensualité",
            "charges",
            "loyer_reçu",
            "loyer_évité",
            "loyer",
            "différence_flux_avec_achat",
            "produit_net_de_vente",
            "cashflows",
        ]
        sum_cols = [c for c in candidate_sum_cols if c in df_m.columns]
        candidate_last_cols = [
            "investissement",
            "cashflows_cumulés",
            "valeur_du_bien",
            "solde_restant_du_crédit",
            "capital_investi",
        ]
        last_cols = [c for c in candidate_last_cols if c in df_m.columns]
        grouped = df_m.groupby("année")
        df_sum = grouped[sum_cols].sum().reset_index() if sum_cols else grouped.size().reset_index(name="_dummy")
        df_last = grouped[last_cols].last().reset_index() if last_cols else grouped.size().reset_index(name="_dummy2")
        return pd.merge(df_sum, df_last, on="année", how="left")

    # ------------------------- Scenarios ------------------------- #
    def run_buying_1(self) -> Dict[str, object]:
        # Compute monthly first, then aggregate to annual for outputs
        df_monthly = self._buying_1_monthly()
        df_annual = self._aggregate_monthly_to_annual(df_monthly)
        cashflows = df_annual["cashflows"].astype(float).tolist()
        sale_proceeds_at_sale = float(self.sale_proceeds(self.n_sale_years)) if self.n_sale_years > 0 else 0.0
        res = {
            "cashflows": cashflows,
            "annuel": df_annual,
            "irr": irr_fn(cashflows),
            "npv": npv_fn(self.inputs.discount_rate, cashflows),
            "mensualité": self.amort.payment_monthly,
            "produit_net_de_vente": sale_proceeds_at_sale,
            "mensuel": df_monthly,
        }
        return res

    def run_buying_2(self) -> Dict[str, object]:
        # Monthly-first rental computation
        df_monthly = self._buying_2_monthly()
        df_annual = self._aggregate_monthly_to_annual(df_monthly)
        cashflows = df_annual["cashflows"].astype(float).tolist()
        res = {
            "cashflows": cashflows,
            "annuel": df_annual,
            "irr": irr_fn(cashflows),
            "npv": npv_fn(self.inputs.discount_rate, cashflows),
            "mensualité": self.amort.payment_monthly,
            "produit_net_de_vente": self.sale_proceeds(self.n_years) if self.n_years > 0 else 0.0,
            "mensuel": df_monthly,
        }
        return res

    def run_renting(self, scenario: str = "buying_1") -> Dict[str, object]:
        """Monthly-first IF scenario with annual aggregation and tax on gains at horizon."""
        df_m = self._renting_monthly(scenario)
        # Annual aggregation (exclude year 0 for grouping)
        df_m_pos = df_m[df_m["année"] >= 1].copy()
        grouped = df_m_pos.groupby("année")
        # Last-of-year apport/loyer/net and cumulative_cash
        df_last = grouped[["investissement", "cashflows_cumulés", "capital_investi"]].last().reset_index()
        # Sum cashflows per year
        df_sum = grouped[["loyer", "différence_flux_avec_achat", "cashflows"]].sum().reset_index()
        df_a = pd.merge(df_last, df_sum, on="année", how="left")
        # Prepend first annual row (year 0) mirroring the first monthly row
        try:
            row0 = df_m.loc[df_m["année"] == 0].iloc[0]
            first_annual = {
                "année": 0,
                "loyer": float(row0.get("loyer", 0.0)),
                "différence_flux_avec_achat": float(row0.get("différence_flux_avec_achat", 0.0)),
                "investissement": float(row0.get("investissement", 0.0)),
                "cashflows": float(row0.get("cashflows", 0.0)),
                "cashflows_cumulés": float(row0.get("cashflows_cumulés", 0.0)),
                "capital_investi": float(row0.get("capital_investi", 0.0)),
            }
            df_a = pd.concat([pd.DataFrame([first_annual]), df_a], ignore_index=True)
        except (IndexError, KeyError):
            pass
        # Build apport_series y=0..N from monthly last apport of each year, prepend y0
        invested_value_series = [float(df_m.loc[df_m["année"] == 0, "investissement"].values[0])] + [
            float(v) for v in df_last["investissement"].tolist()
        ]
        # Annual cashflows including CF0 from df_a
        bm_cfs = df_a["cashflows"].astype(float).tolist()
        return {"cashflows": bm_cfs, "annuel": df_a, "mensuel": df_m, "investissement": invested_value_series}

    # Convenience
    def irr(self, scenario: str = "buying_1") -> Optional[float]:
        if scenario == "buying_1":
            return irr_fn(self.run_buying_1()["cashflows"])  # type: ignore[index]
        if scenario == "buying_2":
            return irr_fn(self.run_buying_2()["cashflows"])  # type: ignore[index]
        return None

    def npv(self, discount_rate: Optional[float] = None, scenario: str = "buying_1") -> Optional[float]:
        rate = self.inputs.discount_rate if discount_rate is None else float(discount_rate)
        if scenario == "renting_1":
            return npv_fn(rate, self.run_renting("buying_1")["cashflows"])  # type: ignore[index]
        if scenario == "renting_2":
            return npv_fn(rate, self.run_renting("buying_2")["cashflows"])  # type: ignore[index]
        if scenario == "buying_1":
            return npv_fn(rate, self.run_buying_1()["cashflows"])  # type: ignore[index]
        if scenario == "buying_2":
            return npv_fn(rate, self.run_buying_2()["cashflows"])  # type: ignore[index]
        return None


