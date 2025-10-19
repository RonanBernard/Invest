from __future__ import annotations

from typing import Dict, List, Optional
import pandas as pd
import plotly.graph_objects as go


def cashflow_bars(yearly_df: pd.DataFrame, title: str = "Cashflow annuel") -> go.Figure:
    fig = go.Figure()
    fig.add_bar(x=yearly_df["year"], y=yearly_df["cashflow"], name="Cashflow")
    fig.update_layout(title=title, xaxis_title="Année", yaxis_title="€")
    return fig


def net_worth_curve(
    owner_df: Optional[pd.DataFrame],
    rental_df: Optional[pd.DataFrame],
    benchmark_series: Optional[List[float]],
    purchase_year: int,
) -> go.Figure:
    fig = go.Figure()
    x_owner = (
        owner_df["year"].apply(lambda y: purchase_year + y).tolist() if owner_df is not None else []
    )
    x_rental = (
        rental_df["year"].apply(lambda y: purchase_year + y).tolist() if rental_df is not None else []
    )

    if owner_df is not None:
        fig.add_trace(go.Scatter(x=x_owner, y=owner_df["net_worth"], mode="lines", name="Patrimoine RP"))
    if rental_df is not None:
        fig.add_trace(go.Scatter(x=x_rental, y=rental_df["net_worth"], mode="lines", name="Patrimoine Location"))
    if benchmark_series is not None and len(benchmark_series) > 1:
        # Build cumulative wealth for benchmark as just the invested amount growth (no property)
        years = list(range(1, len(benchmark_series)))
        x_bm = [purchase_year + y for y in years]
        fig.add_trace(
            go.Scatter(x=x_bm, y=benchmark_series[1:], mode="lines", name="Benchmark Apport")
        )

    fig.update_layout(title="Patrimoine net cumulé", xaxis_title="Année", yaxis_title="€")
    return fig


def sale_waterfall(components: Dict[str, float], title: str = "Vente - Waterfall") -> go.Figure:
    labels = [
        "Prix de vente",
        "Frais de vente",
        "Solde du crédit",
        "Impôt PV",
        "Produit net",
    ]
    base = components.get("sale_price", 0.0)
    selling = -abs(components.get("selling_fees", 0.0))
    crd = -abs(components.get("outstanding_balance", 0.0))
    tax_pv = -abs(components.get("capital_gains_tax", 0.0))
    net = components.get("net_proceeds", 0.0)

    fig = go.Figure(
        go.Waterfall(
            x=labels,
            measure=["relative", "relative", "relative", "relative", "total"],
            y=[base, selling, crd, tax_pv, net],
        )
    )
    fig.update_layout(title=title, yaxis_title="€")
    return fig


def irr_sensitivity_curve(xs: List[float], ys: List[float], x_label: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers"))
    fig.update_layout(
        title=f"Sensibilité IRR vs {x_label}", xaxis_title=x_label, yaxis_title="IRR"
    )
    return fig


# Generic curve for delta NPV
def delta_npv_curve(xs: List[float], ys: List[float], x_label: str) -> go.Figure:
    fig = go.Figure(go.Scatter(x=xs, y=ys, mode="lines+markers"))
    fig.update_layout(
        title=f"Δ NPV (RP vs Benchmark) vs {x_label}", xaxis_title=x_label, yaxis_title="€"
    )
    return fig


def delta_npv_surface(
    x_vals: List[float],
    y_vals: List[float],
    z_matrix: List[List[float]],
    x_label: str,
    y_label: str,
) -> go.Figure:
    """3D surface for Δ NPV over two parameters.

    x_vals: list of x axis values (e.g., price growth)
    y_vals: list of y axis values (e.g., benchmark return)
    z_matrix: len(y_vals) rows, each len(x_vals) columns
    """
    fig = go.Figure(
        data=[
            go.Surface(
                x=x_vals,
                y=y_vals,
                z=z_matrix,
                colorscale="Viridis",
                contours={
                    "z": {
                        "show": True,
                        "usecolormap": True,
                        "highlightcolor": "white",
                        "project_z": True,
                    }
                },
            )
        ]
    )
    fig.update_layout(
        title="Δ NPV (RP vs Benchmark)",
        scene=dict(
            xaxis_title=x_label,
            yaxis_title=y_label,
            zaxis_title="Δ NPV (€)",
        ),
        margin=dict(l=0, r=0, b=0, t=40),
    )
    return fig

