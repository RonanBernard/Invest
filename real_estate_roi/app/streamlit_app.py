from __future__ import annotations

import io
import os
import sys
from dataclasses import asdict
from typing import Dict, List

import numpy as np
import pandas as pd
import streamlit as st
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

# Ensure package import works on Streamlit Cloud when CWD != repo root
_THIS_DIR = os.path.dirname(__file__)
_REPO_ROOT = os.path.abspath(os.path.join(_THIS_DIR, "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from real_estate_roi.core.model_v2 import InvestmentInputs, RealEstateModel
from real_estate_roi.core import plots
from real_estate_roi.core.utils import monthly_rate_from_annual, npv as npv_fn
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
    EVALUATION_YEARS,
    OCCUPANCY_RATE,
    RENT_MONTHLY,
    RENT_GROWTH_RATE,
    MANAGEMENT_FEE_RATE,
    RENTAL_TAX_RATE,
    SELLING_FEES_RATE,
    CAPITAL_GAINS_EFF_RATE,
    INCLUDE_EARLY_REPAYMENT_PENALTY,
    BENCHMARK_RENT_MONTHLY,
    FINANCIAL_INVESTMENT_TAX_RATE,
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

    st.sidebar.subheader("Évolution & horizons")
    price_growth_rate = st.sidebar.number_input("Évolution prix immo (% annuel)", min_value=-100.0, max_value=100.0, value=PRICE_GROWTH_RATE * 100.0, step=0.1, format="%0.1f")
    price_growth_rate = price_growth_rate / 100.0
    inflation_rate = st.sidebar.number_input("Inflation (% annuel)", min_value=-100.0, max_value=100.0, value=INFLATION_RATE * 100.0, step=0.1, format="%0.1f")
    inflation_rate = inflation_rate / 100.0
    discount_rate_input = st.sidebar.number_input("Taux d'actualisation (% annuel)", min_value=-100.0, max_value=100.0, value=DISCOUNT_RATE * 100.0, step=0.1, format="%0.1f")
    discount_rate = discount_rate_input / 100.0
    # Horizons: sale horizon (vente) and evaluation horizon (KPIs)
    horizon_years = int(st.sidebar.number_input("Horizon avant vente (années)", min_value=1, value=int(INVEST_DURATION), step=1))
    purchase_year = int(datetime.datetime.now().year)
    sale_year = int(purchase_year + horizon_years)
    evaluation_years = int(st.sidebar.number_input("Horizon d'évaluation (années)", min_value=1, value=int(EVALUATION_YEARS), step=1))

    st.sidebar.subheader("Location")
    occupancy_rate = st.sidebar.number_input("Taux d'occupation %", min_value=0.0, max_value=100.0, value=OCCUPANCY_RATE * 100.0, step=0.1, format="%0.1f")
    occupancy_rate = occupancy_rate / 100.0
    rent_monthly = st.sidebar.number_input("Loyer mensuel €", min_value=0, value=int(RENT_MONTHLY), step=50)
    rent_growth_rate = st.sidebar.number_input("Croissance loyer (% annuel)", min_value=0.0, max_value=100.0, value=RENT_GROWTH_RATE * 100.0, step=0.1, format="%0.1f")
    rent_growth_rate = rent_growth_rate / 100.0
    management_fee_rate = st.sidebar.number_input("Frais gestion (% du loyer)", min_value=0.0, max_value=100.0, value=MANAGEMENT_FEE_RATE * 100.0, step=0.1, format="%0.1f")
    management_fee_rate = management_fee_rate / 100.0
    rental_tax_rate = st.sidebar.number_input("Fiscalité locative (taux effectif %)", min_value=0.0, max_value=100.0, value=RENTAL_TAX_RATE * 100.0, step=0.1, format="%0.1f")
    rental_tax_rate = rental_tax_rate / 100.0

    st.sidebar.subheader("Investissement financier (IF)")
    benchmark_return_rate = st.sidebar.number_input("Rendement IF (% annuel)", min_value=0.0, max_value=100.0, value=BENCHMARK_RETURN_RATE * 100.0, step=0.1, format="%0.1f")
    benchmark_return_rate = benchmark_return_rate / 100.0
    benchmark_rent_monthly = st.sidebar.number_input("Loyer à payer dans l'IF (€/mois)", min_value=0, value=int(BENCHMARK_RENT_MONTHLY), step=50)
    fi_tax_rate_input = st.sidebar.number_input("Taxe sur IF à l'échéance (% du capital)", min_value=0.0, max_value=100.0, value=FINANCIAL_INVESTMENT_TAX_RATE * 100.0, step=0.1, format="%0.1f")
    financial_investment_tax_rate = fi_tax_rate_input / 100.0

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
        evaluation_years=evaluation_years,
        occupancy_rate=occupancy_rate,
        rent_monthly=rent_monthly,
        rent_growth_rate=rent_growth_rate,
        management_fee_rate=management_fee_rate,
        rental_tax_rate=rental_tax_rate,
        selling_fees_rate=selling_fees_rate,
        capital_gains_eff_rate=capital_gains_eff_rate,
        benchmark_rent_monthly=benchmark_rent_monthly,
        financial_investment_tax_rate=financial_investment_tax_rate,
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


def render_summary(renting_1_res: Dict[str, object], renting_2_res: Dict[str, object], buying_1_res: Dict[str, object], buying_2_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Résumé")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        kpi_card("Mensualité", f"{model.amort.payment_monthly:,.0f} €")
    # NPV des cashflows (taux d'actualisation unifié)
    discount = float(model.inputs.discount_rate)

    # NPV par scénario
    buying_1_npv = float(model.npv(discount_rate=discount, scenario="buying_1") or 0.0)
    buying_2_npv = float(model.npv(discount_rate=discount, scenario="buying_2") or 0.0)
    renting_1_npv = float(model.npv(discount_rate=discount, scenario="renting_1") or 0.0)
    renting_2_npv = float(model.npv(discount_rate=discount, scenario="renting_2") or 0.0)
    # Cumulés
    buying_1_cum = float(sum(buying_1_res.get("cashflows", [])))
    buying_2_cum = float(sum(buying_2_res.get("cashflows", [])))
    renting_1_cum = float(sum(renting_1_res.get("cashflows", [])))
    renting_2_cum = float(sum(renting_2_res.get("cashflows", [])))

    with c2:
        st.markdown("**Location 1 vs Achat 1**")
        kpi_card("NPV (Location 1)", f"{renting_1_npv:,.0f} €")
        st.markdown("&nbsp;", unsafe_allow_html=True)
        kpi_card("Cumulé (Location 1)", f"{renting_1_cum:,.0f} €")
    with c3:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        kpi_card("NPV (Achat 1)", f"{buying_1_npv:,.0f} €")
        st.caption(f"Δ (Achat 1 − Location 1): {(buying_1_npv - renting_1_npv):,.0f} €")
        kpi_card("Cumulé (Achat 1)", f"{buying_1_cum:,.0f} €")
        st.caption(f"Δ cumulé (Achat 1 − Location 1): {(buying_1_cum - renting_1_cum):,.0f} €")
    with c4:
        st.markdown("**Location 2 vs Achat 2**")
        kpi_card("NPV (Location 2)", f"{renting_2_npv:,.0f} €")
        st.markdown("&nbsp;", unsafe_allow_html=True)
        kpi_card("Cumulé (Location 2)", f"{renting_2_cum:,.0f} €")
    with c5:
        st.markdown("&nbsp;", unsafe_allow_html=True)
        kpi_card("NPV (Achat 2)", f"{buying_2_npv:,.0f} €")
        st.caption(f"Δ (Achat 2 − Location 2): {(buying_2_npv - renting_2_npv):,.0f} €")
        kpi_card("Cumulé (Achat 2)", f"{buying_2_cum:,.0f} €")
        st.caption(f"Δ cumulé (Achat 2 − Location 2): {(buying_2_cum - renting_2_cum):,.0f} €")

    if model.inputs.sale_year < model.inputs.purchase_year + 2:
        st.warning("Attention: année de vente < année d'achat + 2 ans (simplification fiscale)")


def render_graphs(renting_1_res: Dict[str, object], renting_2_res: Dict[str, object], buying_1_res: Dict[str, object], buying_2_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Graphiques")
    renting_1_df = renting_1_res["annuel"]  # type: ignore[index]
    renting_2_df = renting_2_res["annuel"]  # type: ignore[index]
    buying_1_df = buying_1_res["annuel"]  # type: ignore[index]
    buying_2_df = buying_2_res["annuel"]  # type: ignore[index]

    c1, c2 = st.columns(2)
    with c1:
        xs_1 = [int(model.inputs.purchase_year + int(y)) for y in renting_1_df["année"].tolist()]
        series_1 = {
            "Location 1": [float(v) for v in renting_1_df["cashflows_cumulés"].tolist()],
            "Achat 1": [float(v) for v in buying_1_df["cashflows_cumulés"].tolist()],
        }
        fig1 = plots.npv_multi_curve(xs_1, series_1, "Année", title="Cumul cashflows - Location 1 vs Achat 1")
        st.plotly_chart(fig1, use_container_width=True)
        st.download_button("Exporter PNG (Cumul L1 vs A1)", data=fig1.to_image(format="png"), file_name="cumul_L1_A1.png", mime="image/png")
    with c2:
        xs_2 = [int(model.inputs.purchase_year + int(y)) for y in renting_2_df["année"].tolist()]
        series_2 = {
            "Location 2": [float(v) for v in renting_2_df["cashflows_cumulés"].tolist()],
            "Achat 2": [float(v) for v in buying_2_df["cashflows_cumulés"].tolist()],
        }
        fig2 = plots.npv_multi_curve(xs_2, series_2, "Année", title="Cumul cashflows - Location 2 vs Achat 2")
        st.plotly_chart(fig2, use_container_width=True)
        st.download_button("Exporter PNG (Cumul L2 vs A2)", data=fig2.to_image(format="png"), file_name="cumul_L2_A2.png", mime="image/png")


def render_tables(renting_1_res: Dict[str, object], renting_2_res: Dict[str, object], buying_1_res: Dict[str, object], buying_2_res: Dict[str, object], model: RealEstateModel):
    st.subheader("Tableaux")
    view_monthly = st.toggle("Voir en mensuel", value=False)

    if not view_monthly:
        # IF-Vente avant Vente
        st.markdown("Cashflows - Location 1 (annuel)")
        renting_1_annual_df = renting_1_res["annuel"]  # type: ignore[index]

        st.dataframe(style_with_commas(renting_1_annual_df), use_container_width=True)

        st.download_button(
            "Exporter CSV Location 1",
            data=renting_1_annual_df.to_csv(index=False).encode("utf-8"),
            file_name="location_1_annuel.csv",
            mime="text/csv",
        )

        st.markdown("Amortissement (annuel)")
        amort_yearly = model.amort_yearly.copy()
        amort_yearly["cashflows"] = -amort_yearly["mensualité"]
        init_row_yearly = {
            "année": 0,
            "mensualité": 0.0,
            "intérêts": 0.0,
            "principal": 0.0,
            "solde_restant_du_crédit": float(model.loan_principal_value),
            "cashflows": -float(model.inputs.down_payment),
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

        st.markdown("Cashflows - Achat 1 (annuel)")
        buying_1_annual_df = buying_1_res["annuel"]  # type: ignore[index]

        st.dataframe(style_with_commas(buying_1_annual_df), use_container_width=True)
        # IRA just above sale proceeds (computed at sale year)
        ira_buying_1 = model.early_repayment_penalty(model.n_sale_years)
        st.download_button(
            "Exporter CSV Vente 1",
            data=buying_1_annual_df.to_csv(index=False).encode("utf-8"),
            file_name="cashflows_vente_1_annuel.csv",
            mime="text/csv",
        )
        st.markdown(f"IRA (indemnités remboursement anticipé): {ira_buying_1:,.0f} €")
        st.markdown(f"Produit net de vente 1 (fin): {buying_1_res.get('produit_net_de_vente', 0.0):,.0f} €")

        # Location 2 avant Achat 2
        st.markdown("Cashflows - Location 2 (annuel)")
        renting_2_annual_df = renting_2_res["annuel"]  # type: ignore[index]
        st.dataframe(style_with_commas(renting_2_annual_df), use_container_width=True)
        st.download_button(
            "Exporter CSV Location 2",
            data=renting_2_annual_df.to_csv(index=False).encode("utf-8"),
            file_name="location_2_annuel.csv",
            mime="text/csv",
        )

        st.markdown("Cashflows - Achat 2 (annuel)")
        buying_2_annual_df = buying_2_res["annuel"]  # type: ignore[index]
        st.dataframe(style_with_commas(buying_2_annual_df), use_container_width=True)
        # IRA for rental table: at evaluation end or sale year? Use sale year for consistency
        ira_buying_2 = model.early_repayment_penalty(model.n_years)
        st.download_button(
            "Exporter CSV Achat 2",
            data=buying_2_annual_df.to_csv(index=False).encode("utf-8"),
            file_name="cashflows_achat_2_annuel.csv",
            mime="text/csv",
        )
        st.markdown(f"IRA (indemnités remboursement anticipé): {ira_buying_2:,.0f} €")
        st.markdown(f"Produit net de vente 2 (fin): {buying_2_res.get('produit_net_de_vente', 0.0):,.0f} €")

        return

    # ---- Monthly view ---- #
    # IF-Vente – tableau mensuel en premier
    st.markdown("Cashflows - Location 1 (mensuel)")
    renting_1_monthly_df = renting_1_res["mensuel"]  # type: ignore[index]
    st.dataframe(style_with_commas(renting_1_monthly_df), use_container_width=True)
    st.download_button(
        "Exporter CSV Location 1 (mensuel)",
        data=renting_1_monthly_df.to_csv(index=False).encode("utf-8"),
        file_name="location_1_mensuel.csv",
        mime="text/csv",
    )

    st.markdown("Amortissement (mensuel)")
    amort_monthly = model.amort.schedule_monthly.copy()
    amort_monthly["cashflows"] = -amort_monthly["mensualité"]
    init_row_monthly = {
        "année": 0,
        "mois": 0,
        "mensualité": 0.0,
        "intérêts": 0.0,
        "principal": 0.0,
        "solde_restant_du_crédit": float(model.loan_principal_value),
        "cashflows": -float(model.inputs.down_payment),
    }
    amort_monthly = pd.concat(
        [pd.DataFrame([init_row_monthly]), amort_monthly], ignore_index=True
    ).sort_values("mois_global").reset_index(drop=True)
    st.dataframe(style_with_commas(amort_monthly), use_container_width=True)
    st.download_button(
        "Exporter CSV Amortissement (mensuel)",
        data=amort_monthly.to_csv(index=False).encode("utf-8"),
        file_name="amortissement_mensuel.csv",
        mime="text/csv",
    )

    # Use monthly data from model
    buying_1_monthly_df = buying_1_res["mensuel"]  # type: ignore[index]
    st.markdown("Cashflows - Achat 1 (mensuel)")
    st.dataframe(style_with_commas(buying_1_monthly_df), use_container_width=True)
    st.download_button(
        "Exporter CSV Achat 1 (mensuel)",
        data=buying_1_monthly_df.to_csv(index=False).encode("utf-8"),
        file_name="cashflows_achat_1_mensuel.csv",
        mime="text/csv",
    )
    st.markdown(f"Produit net de vente 1 (fin): {buying_1_res.get('produit_net_de_vente', 0.0):,.0f} €")

    # IF-Location avant Location
    st.markdown("Cashflows - Location 2 (mensuel)")
    renting_2_monthly_df = renting_2_res["mensuel"]  # type: ignore[index]
    st.dataframe(style_with_commas(renting_2_monthly_df), use_container_width=True)
    st.download_button(
        "Exporter CSV Location 2 (mensuel)",
        data=renting_2_monthly_df.to_csv(index=False).encode("utf-8"),
        file_name="location_2_mensuel.csv",
        mime="text/csv",
    )

    # Use monthly data from model
    st.markdown("Cashflows - Achat 2 (mensuel)")
    buying_2_monthly_df = buying_2_res["mensuel"]  # type: ignore[index]
    # Map rent_personal to rent for consistency
    st.dataframe(style_with_commas(buying_2_monthly_df), use_container_width=True)
    st.download_button(
        "Exporter CSV Achat 2 (mensuel)",
        data=buying_2_monthly_df.to_csv(index=False).encode("utf-8"),
        file_name="cashflows_achat_2_mensuel.csv",
        mime="text/csv",
    )
    st.markdown(f"Produit net de vente 2 (fin): {buying_2_res.get('produit_net_de_vente', 0.0):,.0f} €")

    # (Removed duplicate monthly benchmark table to avoid confusion)


def render_sensitivity(model: RealEstateModel):
    st.subheader("Sensibilité NPV par scénario")

    # Toggle to switch between NPV and Cumulated cashflows
    view_cumulated = st.toggle("Afficher Cumulé (au lieu de NPV)", value=False)
    metric_title = "Cumulé par scénario" if view_cumulated else "NPV par scénario"

    def metric_for(temp_inputs: InvestmentInputs) -> Dict[str, float]:
        m = RealEstateModel(temp_inputs)
        if view_cumulated:
            buying_1 = float(sum(m.run_buying_1().get("cashflows", [])))  # type: ignore[arg-type]
            buying_2 = float(sum(m.run_buying_2().get("cashflows", [])))  # type: ignore[arg-type]
            renting_1 = float(sum(m.run_renting("buying_1").get("cashflows", [])))  # type: ignore[arg-type]
            renting_2 = float(sum(m.run_renting("buying_2").get("cashflows", [])))  # type: ignore[arg-type]
        else:
            discount = float(temp_inputs.discount_rate)
            buying_1 = float(m.npv(discount, "buying_1") or 0.0)
            buying_2 = float(m.npv(discount, "buying_2") or 0.0)
            renting_1 = float(m.npv(discount, "renting_1") or 0.0)
            renting_2 = float(m.npv(discount, "renting_2") or 0.0)
        
        return {"Achat 1": buying_1, "Achat 2": buying_2, "Location 1": renting_1, "Location 2": renting_2}

    # Style helper: match Location colors to corresponding Achat and make them dotted
    def _style_location_vs_buy(fig):
        color_map = {
            "Achat 1": "#1f77b4",   # blue
            "Location 1": "#1f77b4",
            "Achat 2": "#d62728",   # red
            "Location 2": "#d62728",
        }
        for tr in getattr(fig, "data", []):
            name = getattr(tr, "name", "")
            if name in color_map:
                tr.update(line=dict(color=color_map[name], dash=("dot" if name.startswith("Location") else "solid")))
        return fig

    # Ranges around current values
    pr_min = max(-0.1, model.inputs.price_growth_rate - 0.02)
    pr_max = model.inputs.price_growth_rate + 0.02
    ar_min = max(0.0, model.inputs.benchmark_return_rate - 0.02)
    ar_max = model.inputs.benchmark_return_rate + 0.02
    # Evaluation horizons range (ensure >= sale horizon + 1)
    eval_base = int(getattr(model.inputs, "evaluation_years", model.n_years))
    eval_min = max(int(model.n_sale_years) + 1, eval_base - 2)
    eval_max = max(eval_min + 1, eval_base + 2)

    price_rates = np.linspace(pr_min, pr_max, 9).tolist()
    eval_horizons = list(range(eval_min, eval_max + 1))
    alt_returns = np.linspace(ar_min, ar_max, 9).tolist()

    c1, c2, c3 = st.columns(3)
    with c1:
        # Horizon avant vente (years from purchase to sale)
        base_sale_h = int(model.n_sale_years)
        h_min = max(1, base_sale_h - 2)
        h_max = max(h_min + 1, base_sale_h + 2)
        sale_horizons = list(range(h_min, h_max + 1))
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for h in sale_horizons:
            data = asdict(model.inputs)
            data["sale_year"] = int(model.inputs.purchase_year + int(h))
            # Keep evaluation horizon fixed if possible, but ensure >= sale + 1
            base_eval = int(model.inputs.evaluation_years)
            data["evaluation_years"] = int(max(base_eval, int(h) + 1))
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve([float(h) for h in sale_horizons], series, "Horizon avant vente (années)", title=metric_title)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for h in eval_horizons:
            data = asdict(model.inputs)
            # keep sale_year fixed; vary evaluation horizon
            data["evaluation_years"] = int(max(h, int(model.n_sale_years) + 1))
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve([float(h) for h in eval_horizons], series, "Horizon d'évaluation (années)", title=metric_title)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)
    with c3:
        # Taux crédit
        lr_min = max(0.0, float(model.inputs.loan_rate) - 0.02)
        lr_max = float(model.inputs.loan_rate) + 0.02
        loan_rates = np.linspace(lr_min, lr_max, 9).tolist()
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for r in loan_rates:
            data = asdict(model.inputs)
            data["loan_rate"] = float(r)
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve(loan_rates, series, "Taux crédit", title=metric_title, percent_x=True)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)


    # Second row of sensitivities
    c4, c5, c6 = st.columns(3)
    with c4:
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for r in price_rates:
            data = asdict(model.inputs)
            data["price_growth_rate"] = float(r)
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve(price_rates, series, "Évolution prix immo", title=metric_title, percent_x=True)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)

    with c5:
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for r in alt_returns:
            data = asdict(model.inputs)
            data["benchmark_return_rate"] = float(r)
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve(alt_returns, series, "Rendement investissement financier", title=metric_title, percent_x=True)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)

    with c6:
        # Apport (en faisant varier le montant d'apport)
        dp_base = float(model.inputs.down_payment)
        dp_min = max(0.0, dp_base * 0.8)
        dp_max = max(dp_min + 1.0, dp_base * 1.2)
        down_payments = np.linspace(dp_min, dp_max, 9).tolist()
        series = {"Achat 1": [], "Achat 2": [], "Location 1": [], "Location 2": []}
        for a in down_payments:
            data = asdict(model.inputs)
            data["down_payment"] = float(a)
            vals = metric_for(InvestmentInputs(**data))
            for k in series:
                series[k].append(vals[k])
        fig = plots.npv_multi_curve([float(x) for x in down_payments], series, "Apport (€)", title=metric_title)
        fig = _style_location_vs_buy(fig)
        st.plotly_chart(fig, use_container_width=True)


def render_report(renting_1_res: Dict[str, object], renting_2_res: Dict[str, object], buying_1_res: Dict[str, object], buying_2_res: Dict[str, object], model: RealEstateModel):
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
        story.append(Paragraph(f"IRR (Vente): {irr_owner:.2%}" if irr_owner is not None else "IRR (Vente): -", styles["Normal"]))
        story.append(Paragraph(f"IRR (Location): {irr_rental:.2%}" if irr_rental is not None else "IRR (Location): -", styles["Normal"]))
        story.append(Paragraph(f"NPV (Vente): {owner_res.get('npv', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"NPV (Location): {rental_res.get('npv', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"Produit net de vente (fin): {owner_res.get('sale_proceeds', 0.0):,.0f} €".replace(",", " "), styles["Normal"]))
        story.append(Paragraph(f"IF apport (final): {model.financial_investment():,.0f} €".replace(",", " "), styles["Normal"]))
        doc.build(story)
        buffer.seek(0)
        st.download_button("Télécharger PDF", data=buffer, file_name="rapport.pdf", mime="application/pdf")


def main():
    st.title("Calculateur de rentabilité immobilière")
    inputs = sidebar_inputs()
    model = RealEstateModel(inputs)

    renting_1_res = model.run_renting("buying_1")
    renting_2_res = model.run_renting("buying_2")
    buying_1_res = model.run_buying_1()
    buying_2_res = model.run_buying_2()

    tabs = st.tabs(["Résumé", "Graphiques", "Tableaux", "Sensibilité", "Explication des scénarios"])
    with tabs[0]:
        render_summary(renting_1_res, renting_2_res, buying_1_res, buying_2_res, model)
    with tabs[1]:
        render_graphs(renting_1_res, renting_2_res, buying_1_res, buying_2_res, model)
    with tabs[2]:
        render_tables(renting_1_res, renting_2_res, buying_1_res, buying_2_res, model)
    with tabs[3]:
        render_sensitivity(model)
    with tabs[4]:
        st.subheader("Explication des scénarios et des cashflows")
        st.markdown(
            """
            Voici comment sont construits les scénarios et leurs flux de trésorerie (cashflows). Par convention, un montant positif est un encaissement, un montant négatif un décaissement.

            Dans chaque cas, un scénario de location est comparé à un scénario d'achat.
            Dans les scénarios de location, le loyer n'est pas compté dans le cashflow. Mais il est pris en compte dans les scénarios d'achats, comme un loyer évité (en positif).

            L'hypothèse a été faite que si le cashflow est positif, il est investi. Si il est négatif, il n'est pas retiré du capital investi.

            - Achat 1 : achat en résidence principale pour occuper le bien jusqu'à sa vente (horizon avant vente), puis l'argent de la vente est investie jusqu'à l'horizon d'évaluation.
                - Cashflows initial : -apport
                - Cashflows avant vente : -mensualité - charges + loyer évité
                - Cashflows à la vente : le produit de la vente est directement investi jusqu'à l'horizon d'évaluation, il n'apparait donc pas dans le cashflow à cette date.
                - Cashflows à l'évaluation : gains - taxations sur les gains + capital investi

            - Location 1 : location du bien occupé, l'apport qui aurait été utilisé pour l'achat est investi jusqu'à l'horizon d'évaluation.
                La différence entre le loyer payé et le coût récurrent total d'Achat 1 est investie.
                - Cashflows initial : -apport
                - Cashflows avant vente d'Achat 1 : mensualité + charges - loyer payé
                - Cashflows après vente d'Achat 1 : 0
                - Cashflows à l'évaluation : gains - taxations sur les gains + capital investi

            - Achat 2 : achat en résidence principale pour occuper le bien jusqu'à horizon de vente, le bien est ensuite mis en location. Le bien n'est plus occupé par l'acheteur, il faut donc que l'acheteur paye un loyer.
                - Cashflows initial : -apport
                - Cashflows avant vente : -mensualité - charges + loyer évité
                - Cashflows après l'horizon de vente : -mensualité - charges + loyers perçus
                - Cashflows à l'évaluation : produit de la vente + gains - taxations sur les gains + capital investi
            
            - Location 2 : location du bien occupé, l'apport qui aurait été utilisé pour l'achat est investi jusqu'à l'horizon d'évaluation.
                La différence entre le loyer payé et le coût récurrent total d'Achat 2 est investie.
                - Cashflows initial : -apport
                - Cashflows avant mise en location d'Achat 2 : mensualité + charges - loyer payé (payés par Location 2)
                - Cashflows après mise en location d'Achat 2 : mensualité + charges - loyers perçus (perçus par Achat 2, pas de loyés payés car Achat 2 et Location 2 payent le même loyer)
                - Cashflows à l'évaluation : gains - taxations sur les gains + capital investi

            Notes complémentaires:
            - L’IRA (indemnités de remboursement anticipé), si activée, est déduite du produit de vente (6 mois d'intérêts).
            - Le « loyer évité » est bien pris en compte dans les scénarios d’achat (Achat 1 / Achat 2) tant que le bien est occupé.
            - Dans les scénarios « Location 1 » / « Location 2 » (investissement financier de référence), la **différence de coûts récurrents** est appliquée chaque mois à l’investissement financier:
              `différence = net des charges du scénario Achat - net des charges du scénario Location`. Si la différence est positive, elle est **investie** (apport supplémentaire) ; si elle est négative, elle n'est pas retirée du capital investi mais apparait dans le cashflow en négatif.
            - Les tableaux « annuel/mensuel » exposent les composantes (paiements, charges, loyers, gains) ainsi que `cashflows` et `cashflows_cumulés`.
            """
        )

    st.divider()
    render_report(renting_1_res, renting_2_res, buying_1_res, buying_2_res, model)


if __name__ == "__main__":
    main()


