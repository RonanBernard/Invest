from __future__ import annotations

import io
from dataclasses import asdict
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

from real_estate_roi.core.model import InvestmentInputs, RealEstateModel
from real_estate_roi.core import plots
from real_estate_roi.core.utils import benchmark_annual_table
from config import (
    PRICE,
    NOTARY_PCT,
    AGENCY_PCT,
    RENOVATION_COSTS,
    EXTRA_FEES,
    LOAN_RATE,
    LOAN_YEARS,
    DOWN_PAYMENT,
    PROPERTY_TAX_ANNUAL,
    OTHER_TAXES_ANNUAL,
    INSURANCE_RATE_ON_INITIAL_PER_YEAR,
    COPRO_CHARGES_ANNUAL,
    COPRO_GROWTH_RATE,
    MAINTENANCE_RATE_OF_VALUE,
    BENCHMARK_RETURN_RATE,
    PRICE_GROWTH_RATE,
    INFLATION_RATE,
    INVEST_DURATION,
    DISCOUNT_RATE,
    OCCUPANCY_RATE,
    RENT_MONTHLY,
    RENT_GROWTH_RATE,
    MANAGEMENT_FEE_RATE,
    RENTAL_TAX_RATE,
    SELLING_FEES_RATE,
    CAPITAL_GAINS_EFF_RATE,
    INCLUDE_EARLY_REPAYMENT_PENALTY,
    BENCHMARK_RENT_MONTHLY,
)


st.set_page_config(page_title="Calculateur rentabilité immobilière", layout="wide")


def default_inputs() -> InvestmentInputs:
    return InvestmentInputs()


def sidebar_inputs() -> InvestmentInputs:
    st.sidebar.header("Hypothèses principales")
    price = st.sidebar.number_input("Prix d'achat", min_value=0, value=int(PRICE), step=5_000)
    notary_pct_input = st.sidebar.number_input("Frais de notaire (%)", min_value=0.0, max_value=100.0, value=NOTARY_PCT * 100.0, step=0.1, format="%0.1f")
    notary_pct = notary_pct_input / 100.0
    agency_pct_input = st.sidebar.number_input("Frais d'agence (%)", min_value=0.0, max_value=100.0, value=AGENCY_PCT * 100.0, step=0.1, format="%0.1f")
    agency_pct = agency_pct_input / 100.0
    renovation_costs = st.sidebar.number_input("Travaux €", min_value=0, value=int(RENOVATION_COSTS), step=1_000)
    extra_fees = st.sidebar.number_input("Frais annexes €", min_value=0, value=int(EXTRA_FEES), step=500)

    st.sidebar.subheader("Crédit")
    loan_rate = st.sidebar.number_input("Taux crédit (% annuel)", min_value=0.0, max_value=100.0, value=LOAN_RATE * 100.0, step=0.1, format="%0.1f")
    loan_rate = loan_rate / 100.0
    loan_years = int(st.sidebar.number_input("Durée (années)", min_value=0, value=int(LOAN_YEARS), step=1))
    down_payment = st.sidebar.number_input("Apport", min_value=0, value=int(DOWN_PAYMENT), step=5_000)

    st.sidebar.subheader("Charges annuelles")
    property_tax_annual = st.sidebar.number_input("Taxe foncière €", min_value=0, value=int(PROPERTY_TAX_ANNUAL), step=100)
    other_taxes_annual = st.sidebar.number_input("Autres taxes €", min_value=0, value=int(OTHER_TAXES_ANNUAL), step=100)
    insurance_rate = st.sidebar.number_input("Assurance (% capital initial/an)", min_value=0.0, max_value=100.0, value=INSURANCE_RATE_ON_INITIAL_PER_YEAR * 100.0, step=0.01, format="%0.2f")
    insurance_rate = insurance_rate / 100.0
    copro_charges_annual = st.sidebar.number_input("Charges copro €", min_value=0, value=int(COPRO_CHARGES_ANNUAL), step=100)
    copro_growth_rate = st.sidebar.number_input("Évolution charges (% annuel)", min_value=0.0, max_value=100.0, value=COPRO_GROWTH_RATE * 100.0, step=0.1, format="%0.1f")
    copro_growth_rate = copro_growth_rate / 100.0
    maintenance_rate_of_value = st.sidebar.number_input("Entretien (% valeur/an)", min_value=0.0, max_value=100.0, value=MAINTENANCE_RATE_OF_VALUE * 100.0, step=0.1, format="%0.1f")
    maintenance_rate_of_value = maintenance_rate_of_value / 100.0

    st.sidebar.subheader("Évolution & horizon")
    price_growth_rate = st.sidebar.number_input("Évolution prix immo (% annuel)", min_value=-100.0, max_value=100.0, value=PRICE_GROWTH_RATE * 100.0, step=0.1, format="%0.1f")
    price_growth_rate = price_growth_rate / 100.0
    inflation_rate = st.sidebar.number_input("Inflation (% annuel)", min_value=-100.0, max_value=100.0, value=INFLATION_RATE * 100.0, step=0.1, format="%0.1f")
    inflation_rate = inflation_rate / 100.0
    discount_rate_input = st.sidebar.number_input("Taux d'actualisation (% annuel)", min_value=-100.0, max_value=100.0, value=DISCOUNT_RATE * 100.0, step=0.1, format="%0.1f")
    discount_rate = discount_rate_input / 100.0
    # Horizon only: compute sale_year from default purchase_year + horizon
    defaults = default_inputs()
    default_horizon = int(INVEST_DURATION)
    horizon_years = int(st.sidebar.number_input("Horizon avant vente (années)", min_value=1, value=default_horizon, step=1))
    purchase_year = int(datetime.datetime.now().year)
    sale_year = int(purchase_year + horizon_years)

    st.sidebar.subheader("Location")
    occupancy_rate = st.sidebar.number_input("Taux d'occupation %", min_value=0.0, max_value=100.0, value=OCCUPANCY_RATE * 100.0, step=0.1, format="%0.1f")
    occupancy_rate = occupancy_rate / 100.0
    rent_monthly = st.sidebar.number_input("Loyer mensuel €", min_value=0, value=int(RENT_MONTHLY), step=50)
    rent_growth_rate = st.sidebar.number_input("Croissance loyer (annuel)", min_value=0.0, max_value=0.2, value=RENT_GROWTH_RATE, step=0.005, format="%0.3f")
    management_fee_rate = st.sidebar.number_input("Frais gestion (% du loyer)", min_value=0.0, max_value=100.0, value=MANAGEMENT_FEE_RATE * 100.0, step=0.1, format="%0.1f")
    management_fee_rate = management_fee_rate / 100.0
    rental_tax_rate = st.sidebar.number_input("Fiscalité locative (taux effectif %)", min_value=0.0, max_value=100.0, value=RENTAL_TAX_RATE * 100.0, step=0.1, format="%0.1f")
    rental_tax_rate = rental_tax_rate / 100.0

    st.sidebar.subheader("Benchmark financier")
    benchmark_return_rate = st.sidebar.number_input("Rendement benchmark (% annuel)", min_value=0.0, max_value=100.0, value=BENCHMARK_RETURN_RATE * 100.0, step=0.1, format="%0.1f")
    benchmark_return_rate = benchmark_return_rate / 100.0
    benchmark_rent_monthly = st.sidebar.number_input("Loyer à payer dans le benchmark (€/mois)", min_value=0, value=int(BENCHMARK_RENT_MONTHLY), step=50)

    st.sidebar.subheader("Vente")
    selling_fees_rate = st.sidebar.number_input("Frais de vente (%)", min_value=0.0, max_value=100.0, value=SELLING_FEES_RATE * 100.0, step=0.1, format="%0.1f")
    selling_fees_rate = selling_fees_rate / 100.0
    capital_gains_eff_rate = st.sidebar.number_input("Impôt plus-value (taux effectif)", min_value=0.0, max_value=1.0, value=CAPITAL_GAINS_EFF_RATE, step=0.01, format="%0.2f")
    include_ira = st.sidebar.toggle(
        "Inclure IRA (indemnités remboursement anticipé)",
        value=INCLUDE_EARLY_REPAYMENT_PENALTY,
        help="Calcule min(6 mois d'intérêts sur CRD, 3% du CRD) et le retranche du produit de vente",
    )

    return InvestmentInputs(
        price=price,
        notary_pct=notary_pct,
        agency_pct=agency_pct,
        renovation_costs=renovation_costs,
        extra_fees=extra_fees,
        loan_rate=loan_rate,
        loan_years=loan_years,
        down_payment=down_payment,
        property_tax_annual=property_tax_annual,
        other_taxes_annual=other_taxes_annual,
        insurance_rate_on_initial_per_year=insurance_rate,
        copro_charges_annual=copro_charges_annual,
        copro_growth_rate=copro_growth_rate,
        maintenance_rate_of_value=maintenance_rate_of_value,
        benchmark_return_rate=benchmark_return_rate,
        price_growth_rate=price_growth_rate,
        inflation_rate=inflation_rate,
        discount_rate=discount_rate,
        purchase_year=purchase_year,
        sale_year=sale_year,
        occupancy_rate=occupancy_rate,
        rent_monthly=rent_monthly,
        rent_growth_rate=rent_growth_rate,
        management_fee_rate=management_fee_rate,
        rental_tax_rate=rental_tax_rate,
        selling_fees_rate=selling_fees_rate,
        capital_gains_eff_rate=capital_gains_eff_rate,
        benchmark_rent_monthly=benchmark_rent_monthly,
        include_early_repayment_penalty=include_ira,
    )


def build_benchmark_series(down_payment: float, rate: float, years: int) -> List[float]:
    series = [down_payment]
    value = down_payment
    for _ in range(1, years + 1):
        value = value * (1 + rate)
        series.append(value)
    return series


def kpi_card(label: str, value: str, help_text: str | None = None):
    st.metric(label, value, help=help_text)


def style_with_commas(df: pd.DataFrame):
    num_cols = df.select_dtypes(include=["number"]).columns
    if len(num_cols) == 0:
        return df
    return df.style.format({col: "{:,.0f}" for col in num_cols})


def render_summary(owner_res: Dict[str, object], rental_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Résumé")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        kpi_card("Mensualité", f"{model.amort.payment_monthly:,.0f} €")
    # NPV des cashflows (taux d'actualisation unifié)
    discount = float(model.inputs.discount_rate)
    owner_npv = float(model.npv(discount_rate=discount, scenario="owner") or 0.0)
    rental_npv = float(model.npv(discount_rate=discount, scenario="rental") or 0.0)
    # Benchmark NPV: construit flux benchmark et applique NPV
    bm_cfs = [-float(model.inputs.down_payment)]
    for y in range(1, model.n_years + 1):
        cf = -12.0 * float(model.inputs.benchmark_rent_monthly)
        if y == model.n_years:
            cf += float(model.benchmark_apport())
        bm_cfs.append(cf)
    # NPV benchmark
    bm_npv = 0.0
    for t, cf in enumerate(bm_cfs):
        bm_npv += cf / ((1 + discount) ** t)
    # Cumulative cashflows
    bm_cum = float(sum(bm_cfs))
    owner_cum = float(sum(owner_res.get("cashflows", [])))
    rental_cum = float(sum(rental_res.get("cashflows", [])))

    with c2:
        kpi_card("NPV (Benchmark)", f"{bm_npv:,.0f} €")
        kpi_card("Cumulé (Benchmark)", f"{bm_cum:,.0f} €")
    with c3:
        kpi_card("NPV (RP)", f"{owner_npv:,.0f} €")
        kpi_card("Cumulé (RP)", f"{owner_cum:,.0f} €")
    with c4:
        kpi_card("NPV (Location)", f"{rental_npv:,.0f} €")
        kpi_card("Cumulé (Location)", f"{rental_cum:,.0f} €")

    if model.inputs.sale_year < model.inputs.purchase_year + 2:
        st.warning("Attention: année de vente < année d'achat + 2 ans (simplification fiscale)")


def render_graphs(owner_res: Dict[str, object], rental_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Graphiques")
    owner_df = owner_res["yearly"]  # type: ignore[index]
    rental_df = rental_res["yearly"]  # type: ignore[index]

    c1, c2 = st.columns(2)
    with c1:
        fig_cf_owner = plots.cashflow_bars(owner_df, title="Cashflow annuel (RP)")
        st.plotly_chart(fig_cf_owner, use_container_width=True)
        png_owner = fig_cf_owner.to_image(format="png")
        st.download_button("Exporter PNG (RP)", data=png_owner, file_name="cashflow_rp.png", mime="image/png")

    with c2:
        fig_cf_rental = plots.cashflow_bars(rental_df, title="Cashflow annuel (Location)")
        st.plotly_chart(fig_cf_rental, use_container_width=True)
        png_rental = fig_cf_rental.to_image(format="png")
        st.download_button("Exporter PNG (Location)", data=png_rental, file_name="cashflow_location.png", mime="image/png")

    benchmark_series = build_benchmark_series(
        down_payment=model.inputs.down_payment, rate=model.inputs.benchmark_return_rate, years=model.n_years
    )
    fig_worth = plots.net_worth_curve(owner_df, rental_df, benchmark_series, model.inputs.purchase_year)
    st.plotly_chart(fig_worth, use_container_width=True)
    st.download_button("Exporter PNG (Patrimoine)", data=fig_worth.to_image(format="png"), file_name="patrimoine.png", mime="image/png")


def render_tables(owner_res: Dict[str, object], rental_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Tableaux")
    view_monthly = st.toggle("Voir en mensuel", value=False)

    if not view_monthly:
        st.markdown("Amortissement (annuel)")
        amort_yearly = model.amort_yearly.copy()
        amort_yearly["cashflow"] = -amort_yearly["payment"]
        init_row_yearly = {
            "year": 0,
            "payment": 0.0,
            "interest": 0.0,
            "principal": 0.0,
            "end_balance": float(model.loan_principal_value),
            "cashflow": -float(model.inputs.down_payment),
        }
        amort_yearly = pd.concat(
            [pd.DataFrame([init_row_yearly]), amort_yearly], ignore_index=True
        )
        st.dataframe(style_with_commas(amort_yearly), use_container_width=True)
        st.download_button(
            "Exporter CSV Amortissement",
            data=amort_yearly.to_csv(index=False).encode("utf-8"),
            file_name="amortissement_annuel.csv",
            mime="text/csv",
        )

        st.markdown("Cashflows - Résidence principale (annuel)")
        owner_df = owner_res["yearly"]  # type: ignore[index]
        owner_df_disp = owner_df.drop(columns=["sale_proceeds"], errors="ignore")
        desired_cols_owner_annual = [
            "year",
            "loan_payment",
            "charges",
            "cashflow",
            "cumulative_cash",
            "property_value",
            "outstanding_balance",
        ]
        owner_df_disp = owner_df_disp[[c for c in desired_cols_owner_annual if c in owner_df_disp.columns]]
        st.dataframe(style_with_commas(owner_df_disp), use_container_width=True)
        st.download_button(
            "Exporter CSV RP",
            data=owner_df_disp.to_csv(index=False).encode("utf-8"),
            file_name="cashflows_rp_annuel.csv",
            mime="text/csv",
        )
        st.markdown(f"Produit net de vente (fin): {owner_res.get('sale_proceeds', 0.0):,.0f} €")

        st.markdown("Cashflows - Location (annuel)")
        rental_df = rental_res["yearly"]  # type: ignore[index]
        rental_df_disp = rental_df.drop(columns=["sale_proceeds"], errors="ignore")
        desired_cols_rental_annual = [
            "year",
            "cashflow",
            "operating_before_debt",
            "loan_payment",
            "charges",
            "rent_gross",
            "cumulative_cash",
            "property_value",
            "outstanding_balance",
        ]
        rental_df_disp = rental_df_disp[[c for c in desired_cols_rental_annual if c in rental_df_disp.columns]]
        st.dataframe(style_with_commas(rental_df_disp), use_container_width=True)
        st.download_button(
            "Exporter CSV Location",
            data=rental_df_disp.to_csv(index=False).encode("utf-8"),
            file_name="cashflows_location_annuel.csv",
            mime="text/csv",
        )
        st.markdown(f"Produit net de vente (fin): {rental_res.get('sale_proceeds', 0.0):,.0f} €")

        # Benchmark apport – tableau annuel Apport / Loyer / Net
        st.markdown("Benchmark apport (annuel)")
        apport_vals, rent_costs, nets = benchmark_annual_table(
            down_payment=model.inputs.down_payment,
            annual_rate=model.inputs.benchmark_return_rate,
            monthly_rent=float(model.inputs.benchmark_rent_monthly),
            years=model.n_years,
        )
        bm_df = pd.DataFrame(
            {
                "year": list(range(0, model.n_years + 1)),
                "apport": apport_vals,
                "loyer": rent_costs,
                "net": nets,
            }
        )
        st.dataframe(style_with_commas(bm_df), use_container_width=True)
        st.download_button(
            "Exporter CSV Benchmark",
            data=bm_df.to_csv(index=False).encode("utf-8"),
            file_name="benchmark_annuel.csv",
            mime="text/csv",
        )
        return

    # ---- Monthly view ---- #
    st.markdown("Amortissement (mensuel)")
    amort_monthly = model.amort.schedule_monthly.copy()
    amort_monthly["cashflow"] = -amort_monthly["payment"]
    init_row_monthly = {
        "month": 0,
        "payment": 0.0,
        "interest": 0.0,
        "principal": 0.0,
        "balance": float(model.loan_principal_value),
        "cashflow": -float(model.inputs.down_payment),
    }
    amort_monthly = pd.concat(
        [pd.DataFrame([init_row_monthly]), amort_monthly], ignore_index=True
    ).sort_values("month").reset_index(drop=True)
    st.dataframe(style_with_commas(amort_monthly), use_container_width=True)
    st.download_button(
        "Exporter CSV Amortissement (mensuel)",
        data=amort_monthly.to_csv(index=False).encode("utf-8"),
        file_name="amortissement_mensuel.csv",
        mime="text/csv",
    )

    # Build monthly owner cashflows (approximation consistent with annual totals)
    months_total = model.inputs.loan_years * 12
    monthly_payment = float(model.amort.payment_monthly)
    cum_cash = -model.inputs.down_payment
    owner_rows = []
    for y in range(1, model.n_years + 1):
        # Annual non-debt charges for the year
        charges_annual = (
            model.inputs.property_tax_annual
            + model.inputs.other_taxes_annual
            + model._copro_charges(y)
            + model._maintenance_cost(y)
            + model._annual_insurance()
        )
        charge_monthly = float(charges_annual) / 12.0
        for m in range(1, 13):
            global_month = (y - 1) * 12 + m
            if global_month > months_total:
                break
            # End-of-month balance from amortization schedule
            try:
                end_balance = float(model.amort.schedule_monthly.loc[model.amort.schedule_monthly["month"] == global_month, "balance"].values[0])
            except IndexError:
                end_balance = 0.0
            cf = -monthly_payment - charge_monthly
            sale_p = 0.0
            if y == model.n_years and m == 12:
                sale_p = float(model.sale_proceeds(y))
                cf += sale_p
            cum_cash += cf
            # Use year-level property value for all months in that year
            prop_val = model._property_value_at(y)
            net_worth = prop_val - end_balance + cum_cash
            owner_rows.append(
                {
                    "year": y,
                    "month": m,
                    "cashflow": cf,
                    "loan_payment": monthly_payment,
                    "charges": charge_monthly,
                    "sale_proceeds": sale_p,
                    "cumulative_cash": cum_cash,
                    "property_value": prop_val,
                    "outstanding_balance": end_balance,
                    "net_worth": net_worth,
                }
            )

    owner_monthly_df = pd.DataFrame(owner_rows)
    st.markdown("Cashflows - Résidence principale (mensuel)")
    owner_monthly_df_disp = owner_monthly_df.drop(columns=["sale_proceeds"], errors="ignore")
    desired_cols_owner_monthly = [
        "year",
        "month",
        "cashflow",
        "loan_payment",
        "charges",
        "cumulative_cash",
        "property_value",
        "outstanding_balance",
    ]
    owner_monthly_df_disp = owner_monthly_df_disp[[c for c in desired_cols_owner_monthly if c in owner_monthly_df_disp.columns]]
    st.dataframe(style_with_commas(owner_monthly_df_disp), use_container_width=True)
    st.download_button(
        "Exporter CSV RP (mensuel)",
        data=owner_monthly_df_disp.to_csv(index=False).encode("utf-8"),
        file_name="cashflows_rp_mensuel.csv",
        mime="text/csv",
    )
    st.markdown(f"Produit net de vente (fin): {model.sale_proceeds(model.n_years):,.0f} €")

    # Build monthly rental cashflows
    cum_cash = -model.inputs.down_payment
    rental_rows = []
    for y in range(1, model.n_years + 1):
        op_annual = model._rental_net_after_tax_before_debt(y)
        op_monthly = float(op_annual) / 12.0
        # Optional: rent gross monthly (for reference)
        rent_gross_monthly = float(model._rental_revenue_gross(y)) / 12.0
        for m in range(1, 13):
            global_month = (y - 1) * 12 + m
            if global_month > months_total:
                break
            try:
                end_balance = float(model.amort.schedule_monthly.loc[model.amort.schedule_monthly["month"] == global_month, "balance"].values[0])
            except IndexError:
                end_balance = 0.0
            cf = op_monthly - monthly_payment
            sale_p = 0.0
            if y == model.n_years and m == 12:
                sale_p = float(model.sale_proceeds(y))
                cf += sale_p
            cum_cash += cf
            prop_val = model._property_value_at(y)
            net_worth = prop_val - end_balance + cum_cash
            charges_monthly = rent_gross_monthly - op_monthly
            rental_rows.append(
                {
                    "year": y,
                    "month": m,
                    "cashflow": cf,
                    "operating_before_debt": op_monthly,
                    "loan_payment": monthly_payment,
                    "charges": charges_monthly,
                    "sale_proceeds": sale_p,
                    "cumulative_cash": cum_cash,
                    "property_value": prop_val,
                    "outstanding_balance": end_balance,
                    "net_worth": net_worth,
                    "rent_gross": rent_gross_monthly,
                }
            )

    rental_monthly_df = pd.DataFrame(rental_rows)
    st.markdown("Cashflows - Location (mensuel)")
    rental_monthly_df_disp = rental_monthly_df.drop(columns=["sale_proceeds"], errors="ignore")
    desired_cols_rental_monthly = [
        "year",
        "month",
        "cashflow",
        "operating_before_debt",
        "loan_payment",
        "charges",
        "rent_gross",
        "cumulative_cash",
        "property_value",
        "outstanding_balance",
    ]
    rental_monthly_df_disp = rental_monthly_df_disp[[c for c in desired_cols_rental_monthly if c in rental_monthly_df_disp.columns]]
    st.dataframe(style_with_commas(rental_monthly_df_disp), use_container_width=True)
    st.download_button(
        "Exporter CSV Location (mensuel)",
        data=rental_monthly_df_disp.to_csv(index=False).encode("utf-8"),
        file_name="cashflows_location_mensuel.csv",
        mime="text/csv",
    )
    st.markdown(f"Produit net de vente (fin): {model.sale_proceeds(model.n_years):,.0f} €")

    st.markdown("Hypothèses")
    st.json(asdict(model.inputs))


def render_sensitivity(model: RealEstateModel):
    st.subheader("Sensibilité IRR")
    # ±2 points around current values
    lr_min = max(0.0, model.inputs.loan_rate - 0.02)
    lr_max = model.inputs.loan_rate + 0.02
    pr_min = max(0.0, model.inputs.price_growth_rate - 0.02)
    pr_max = model.inputs.price_growth_rate + 0.02
    ar_min = max(0.0, model.inputs.benchmark_return_rate - 0.02)
    ar_max = model.inputs.benchmark_return_rate + 0.02

    loan_rates = np.linspace(lr_min, lr_max, 9).tolist()
    price_rates = np.linspace(pr_min, pr_max, 9).tolist()
    alt_returns = np.linspace(ar_min, ar_max, 9).tolist()

    def irr_for(rate: float, kind: str) -> float:
        # Clone inputs and change a single parameter
        data = asdict(model.inputs)
        data[kind] = float(rate)
        m = RealEstateModel(InvestmentInputs(**data))
        return float(m.irr("rental") or 0.0)

    c1, c2, c3 = st.columns(3)
    with c1:
        irr_vals = [irr_for(r, "loan_rate") for r in loan_rates]
        fig = plots.irr_sensitivity_curve(loan_rates, irr_vals, "Taux crédit")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        irr_vals = [irr_for(r, "price_growth_rate") for r in price_rates]
        fig = plots.irr_sensitivity_curve(price_rates, irr_vals, "Évolution prix immo")
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        irr_vals = [irr_for(r, "benchmark_return_rate") for r in alt_returns]
        fig = plots.irr_sensitivity_curve(alt_returns, irr_vals, "Rendement benchmark")
        st.plotly_chart(fig, use_container_width=True)


def render_report(owner_res: Dict[str, object], rental_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Rapport")
    if st.button("Générer PDF"):
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        story.append(Paragraph("Rapport de rentabilité immobilière", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"Mensualité: {model.amort.payment_monthly:,.0f} €".replace(",", " "), styles["Normal"]))
        irr_owner = owner_res.get("irr")
        irr_rental = rental_res.get("irr")
        story.append(Paragraph(f"IRR (RP): {irr_owner:.2%}" if irr_owner is not None else "IRR (RP): -", styles["Normal"]))
        story.append(Paragraph(f"IRR (Location): {irr_rental:.2%}" if irr_rental is not None else "IRR (Location): -", styles["Normal"]))
        story.append(Paragraph(f"NPV (RP): {owner_res.get('npv', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"NPV (Location): {rental_res.get('npv', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"Produit net de vente (fin): {owner_res.get('sale_proceeds', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"Benchmark apport (final): {model.benchmark_apport():,.0f} €".replace(",", " "), styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        st.download_button("Télécharger PDF", data=buffer, file_name="rapport.pdf", mime="application/pdf")


def main():
    st.title("Calculateur de rentabilité immobilière")
    inputs = sidebar_inputs()
    model = RealEstateModel(inputs)

    owner_res = model.run_owner()
    rental_res = model.run_rental()

    tabs = st.tabs(["Résumé", "Graphiques", "Tableaux", "Sensibilité", "Paramètres fiscaux"])
    with tabs[0]:
        render_summary(owner_res, rental_res, model)
    with tabs[1]:
        render_graphs(owner_res, rental_res, model)
    with tabs[2]:
        render_tables(owner_res, rental_res, model)
    with tabs[3]:
        render_sensitivity(model)
    with tabs[4]:
        st.info("Les paramètres fiscaux sont modifiables dans la barre latérale.")
        st.json({
            "rental_tax_rate": inputs.rental_tax_rate,
            "capital_gains_eff_rate": inputs.capital_gains_eff_rate,
            "selling_fees_rate": inputs.selling_fees_rate,
        })

    st.divider()
    render_report(owner_res, rental_res, model)


if __name__ == "__main__":
    main()


