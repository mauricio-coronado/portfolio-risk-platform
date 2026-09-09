import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import matplotlib.ticker as mticker
from matplotlib.patches import FancyBboxPatch
import pandas as pd
import numpy as np

from src.risk_metrics import (
    calculate_cumulative_return, calculate_annualized_volatility,
    calculate_historical_var, calculate_expected_shortfall, calculate_max_drawdown, 
    calculate_tail_count
)
from src.exposure import breakdown_exposure

PALETTE = {
    "primary": "#3B5B92",
    "gross": "#C9CED6",
    "loss": "#C0392B",
    "gain": "#27883D",
    "bg_card": "#F5F6F8",
    "text_dark": "#1E2430",
    "text_muted": "#6B7280",
}

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 10,
    "axes.edgecolor": "#D0D3D8",
    "axes.labelcolor": PALETTE["text_dark"],
    "text.color": PALETTE["text_dark"],
    "axes.grid": True,
    "grid.color": "#E5E7EB",
    "grid.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titlesize": 11,
    "axes.titleweight": "bold",
})


def build_kpi_summary(portfolio_returns: pd.Series) -> dict:
    return {
        "cumulative_return": calculate_cumulative_return(portfolio_returns),
        "annualized_volatility": calculate_annualized_volatility(portfolio_returns),
        "var_95": calculate_historical_var(portfolio_returns, 0.95),
        "var_99": calculate_historical_var(portfolio_returns, 0.99),
        "es_95": calculate_expected_shortfall(portfolio_returns, 0.95),
        "es_99": calculate_expected_shortfall(portfolio_returns, 0.99),
        "tail_n_95": calculate_tail_count(portfolio_returns, 0.95),
        "tail_n_99": calculate_tail_count(portfolio_returns, 0.99),
        "max_drawdown": calculate_max_drawdown(portfolio_returns),
        "valid_days": int(portfolio_returns.notna().sum()),
        "total_days": int(len(portfolio_returns)),
    }


def _draw_kpi_cards(ax_kpi, kpis):
    kpi_items = [
        ("Cumulative Return", f"{kpis['cumulative_return']:.2%}", kpis["cumulative_return"] < 0),
        ("Ann. Volatility", f"{kpis['annualized_volatility']:.2%}", None),
        ("95% VaR (1d)", f"{kpis['var_95']:.2%}", True),
        ("99% VaR (1d)", f"{kpis['var_99']:.2%}", True),
        (f"95% ES (1d, n={kpis['tail_n_95']})", f"{kpis['es_95']:.2%}", True),
        (f"99% ES (1d, n={kpis['tail_n_99']})", f"{kpis['es_99']:.2%}", True),
        ("Max Drawdown", f"{kpis['max_drawdown']:.2%}", True),
        ("Valid Days", f"{kpis['valid_days']}/{kpis['total_days']}", None),
    ]
    n = len(kpi_items)
    for i, (label, value, is_loss) in enumerate(kpi_items):
        x = i / n
        w = 1 / n * 0.92
        card = FancyBboxPatch((x, 0.05), w, 0.9, boxstyle="round,pad=0.01,rounding_size=0.02",
                                transform=ax_kpi.transAxes, facecolor=PALETTE["bg_card"],
                                edgecolor="#E0E2E6", linewidth=1)
        ax_kpi.add_patch(card)
        color = PALETTE["loss"] if is_loss else PALETTE["text_dark"]
        ax_kpi.text(x + w / 2, 0.62, value, transform=ax_kpi.transAxes, ha="center", va="center",
                    fontsize=14, fontweight="bold", color=color)
        ax_kpi.text(x + w / 2, 0.25, label, transform=ax_kpi.transAxes, ha="center", va="center",
                    fontsize=8, color=PALETTE["text_muted"])


def build_dashboard_page(portfolio_returns: pd.Series, weights: pd.DataFrame,
                          equity_shocks, rate_shocks_bps, stress_grid,
                          exposure_dimension: str = "Asset Type") -> plt.Figure:
    """
    Assemble the full single-page risk dashboard in a 2x2 quadrant
    layout: KPI summary cards across the top, cumulative wealth
    (top-left), drawdown (top-right), exposure breakdown by a
    selectable dimension (bottom-left), and a stress sensitivity
    surface (bottom-right).

    Args:
        portfolio_returns (pd.Series): daily portfolio returns.
        weights (pd.DataFrame): PortfolioWeights sheet.
        equity_shocks (array-like): equity shock grid values used to
            build stress_grid (needed here only for axis labeling).
        rate_shocks_bps (array-like): rate shock grid values used to
            build stress_grid (needed here only for axis labeling).
        stress_grid (np.ndarray): output of compute_stress_surface(),
            computed once outside this function since it does not
            depend on portfolio_returns or exposure_dimension, and
            is expensive enough (~1.5s) to be worth not recomputing
            on every date-range or exposure-dimension change.
        exposure_dimension (str): which SecurityMaster dimension to
            show in the exposure panel. Default "Asset Type".

    Returns:
        matplotlib.figure.Figure
    """
    kpis = build_kpi_summary(portfolio_returns)
    clean_returns = portfolio_returns.dropna()
    wealth = (1 + clean_returns).cumprod()
    running_max = wealth.cummax()
    drawdown = (wealth - running_max) / running_max

    fig = plt.figure(figsize=(11, 6))
    gs = gridspec.GridSpec(3, 2, height_ratios=[0.35, 1, 1], hspace=0.7, wspace=0.3,
                            left=0.06, right=0.96, top=0.94, bottom=0.06)

    fig.suptitle("Portfolio Risk Dashboard", fontsize=13, fontweight="bold",
                 x=0.06, ha="left", color=PALETTE["text_dark"], y=0.99)

    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis("off")
    _draw_kpi_cards(ax_kpi, kpis)

    ax_wealth = fig.add_subplot(gs[1, 0])
    ax_wealth.plot(wealth.index, wealth.values, color=PALETTE["primary"], linewidth=1.3)
    ax_wealth.set_title("Cumulative Wealth")
    ax_wealth.set_ylabel("Wealth (growth of $1)")
    ax_wealth.xaxis.set_major_locator(mticker.MaxNLocator(5))
    ax_wealth.tick_params(axis='x', labelsize=9)
    plt.setp(ax_wealth.get_xticklabels(), rotation=20, ha="right")

    ax_dd = fig.add_subplot(gs[1, 1])
    ax_dd.fill_between(drawdown.index, drawdown.values * 100, 0, color=PALETTE["loss"], alpha=0.55)
    ax_dd.set_title("Drawdown from Peak")
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax_dd.tick_params(axis='x', labelsize=9)
    ax_dd.xaxis.set_major_locator(mticker.MaxNLocator(5))

    plt.setp(ax_dd.get_xticklabels(), rotation=20, ha="right")

    ax_exp = fig.add_subplot(gs[2, 0])
    exp_data = breakdown_exposure(weights, exposure_dimension)
    y_pos = range(len(exp_data))
    ax_exp.barh(y_pos, exp_data["gross_exposure"] * 100, color=PALETTE["gross"], height=0.6, label="Gross")
    ax_exp.barh(y_pos, exp_data["net_exposure"] * 100, color=PALETTE["primary"], height=0.3, label="Net")
    ax_exp.set_yticks(list(y_pos))
    ax_exp.set_yticklabels(exp_data.index)
    ax_exp.invert_yaxis()
    ax_exp.set_title(f"Exposure by {exposure_dimension}")
    ax_exp.set_xlabel("Exposure (%)")
    ax_exp.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2)

    ax_stress = fig.add_subplot(gs[2, 1])
    im = ax_stress.pcolormesh(equity_shocks * 100, rate_shocks_bps, stress_grid * 100,
                            cmap="YlOrRd_r", shading="gouraud")
    cbar = fig.colorbar(im, ax=ax_stress, fraction=0.046, pad=0.04)
    cbar.set_label("Portfolio Impact (%)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    equity_only_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 0)), np.argmin(np.abs(equity_shocks - (-0.15)))]
    ax_stress.plot(-15, 0, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5)
    ax_stress.annotate(f"Equity Selloff\n{equity_only_value:.2%}", (-15, 0), textcoords="offset points", xytext=(0, 8), fontsize=7, ha="center")

    rate_only_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - 0))]
    ax_stress.plot(0, 100, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5)
    ax_stress.annotate(f"Rate Shock\n{rate_only_value:.2%}", (0, 100), textcoords="offset points", xytext=(-55, 3), fontsize=7, ha="left")

    ax_stress.plot(-15, 100, marker="*", color="gold", markeredgecolor="black", markersize=13, zorder=5)
    combined_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - (-0.15)))]
    ax_stress.annotate(f"Combined\n{combined_value:.2%}", (-15, 100), textcoords="offset points", xytext=(8, 3), fontsize=7, fontweight="bold")

    ax_stress.set_xlim(-25, 2)
    ax_stress.set_ylim(-5, 210)
    ax_stress.set_xlabel("Equity Shock (%)")
    ax_stress.set_ylabel("Rate Shock (bps)")
    ax_stress.set_title("Stress Sensitivity Surface")

    return fig
