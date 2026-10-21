import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
from matplotlib.patches import FancyBboxPatch

from riskplatform.exposure import breakdown_exposure
from riskplatform.kpis import build_kpi_summary
from riskplatform.risk_metrics import calculate_cumulative_return

PALETTE = {
    "primary": "#3B5B92",
    "gross": "#C9CED6",
    "loss": "#C0392B",
    "gain": "#27883D",
    "bg_card": "#F5F6F8",
    "text_dark": "#1E2430",
    "text_muted": "#6B7280",
}

plt.rcParams.update(
    {
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
    }
)


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
        card = FancyBboxPatch(
            (x, 0.05),
            w,
            0.9,
            boxstyle="round,pad=0.01,rounding_size=0.02",
            transform=ax_kpi.transAxes,
            facecolor=PALETTE["bg_card"],
            edgecolor="#E0E2E6",
            linewidth=1,
        )
        ax_kpi.add_patch(card)
        color = PALETTE["loss"] if is_loss else PALETTE["text_dark"]
        ax_kpi.text(
            x + w / 2,
            0.62,
            value,
            transform=ax_kpi.transAxes,
            ha="center",
            va="center",
            fontsize=14,
            fontweight="bold",
            color=color,
        )
        ax_kpi.text(
            x + w / 2,
            0.25,
            label,
            transform=ax_kpi.transAxes,
            ha="center",
            va="center",
            fontsize=8,
            color=PALETTE["text_muted"],
        )


# def build_dashboard_page(portfolio_returns: pd.Series, weights: pd.DataFrame,
#                           equity_shocks, rate_shocks_bps, stress_grid,
#                           exposure_dimension: str = "Asset Type") -> plt.Figure:
#     """
#     Assemble the full single-page risk dashboard in a 2x2 quadrant
#     layout: KPI summary cards across the top, cumulative wealth
#     (top-left), drawdown (top-right), exposure breakdown by a
#     selectable dimension (bottom-left), and a stress sensitivity
#     surface (bottom-right).

#     Args:
#         portfolio_returns (pd.Series): daily portfolio returns.
#         weights (pd.DataFrame): PortfolioWeights sheet.
#         equity_shocks (array-like): equity shock grid values used to
#             build stress_grid (needed here only for axis labeling).
#         rate_shocks_bps (array-like): rate shock grid values used to
#             build stress_grid (needed here only for axis labeling).
#         stress_grid (np.ndarray): output of compute_stress_surface(),
#             computed once outside this function since it does not
#             depend on portfolio_returns or exposure_dimension, and
#             is expensive enough (~1.5s) to be worth not recomputing
#             on every date-range or exposure-dimension change.
#         exposure_dimension (str): which SecurityMaster dimension to
#             show in the exposure panel. Default "Asset Type".

#     Returns:
#         matplotlib.figure.Figure
#     """
#     kpis = build_kpi_summary(portfolio_returns)
#     clean_returns = portfolio_returns.dropna()
#     wealth = (1 + clean_returns).cumprod()
#     running_max = wealth.cummax()
#     drawdown = (wealth - running_max) / running_max

#     fig = plt.figure(figsize=(11, 6))
#     gs = gridspec.GridSpec(3, 2, height_ratios=[0.35, 1, 1], hspace=0.7, wspace=0.3,
#                             left=0.06, right=0.96, top=0.94, bottom=0.06)

#     fig.suptitle("Portfolio Risk Dashboard", fontsize=13, fontweight="bold",
#                  x=0.06, ha="left", color=PALETTE["text_dark"], y=0.99)

#     ax_kpi = fig.add_subplot(gs[0, :])
#     ax_kpi.axis("off")
#     _draw_kpi_cards(ax_kpi, kpis)

#     ax_wealth = fig.add_subplot(gs[1, 0])
#     ax_wealth.plot(wealth.index, wealth.values, color=PALETTE["primary"], linewidth=1.3)
#     ax_wealth.set_title("Cumulative Wealth")
#     ax_wealth.set_ylabel("Wealth (growth of $1)")
#     ax_wealth.xaxis.set_major_locator(mticker.MaxNLocator(5))
#     ax_wealth.tick_params(axis='x', labelsize=9)
#     plt.setp(ax_wealth.get_xticklabels(), rotation=20, ha="right")

#     ax_dd = fig.add_subplot(gs[1, 1])
#     ax_dd.fill_between(drawdown.index, drawdown.values * 100, 0, color=PALETTE["loss"], alpha=0.55)
#     ax_dd.set_title("Drawdown from Peak")
#     ax_dd.set_ylabel("Drawdown (%)")
#     ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter())
#     ax_dd.tick_params(axis='x', labelsize=9)
#     ax_dd.xaxis.set_major_locator(mticker.MaxNLocator(5))

#     plt.setp(ax_dd.get_xticklabels(), rotation=20, ha="right")

#     ax_exp = fig.add_subplot(gs[2, 0])
#     exp_data = breakdown_exposure(weights, exposure_dimension)
#     y_pos = range(len(exp_data))
#     ax_exp.barh(y_pos, exp_data["gross_exposure"] * 100, color=PALETTE["gross"], height=0.6, label="Gross")
#     ax_exp.barh(y_pos, exp_data["net_exposure"] * 100, color=PALETTE["primary"], height=0.3, label="Net")
#     ax_exp.set_yticks(list(y_pos))
#     ax_exp.set_yticklabels(exp_data.index)
#     ax_exp.invert_yaxis()
#     ax_exp.set_title(f"Exposure by {exposure_dimension}")
#     ax_exp.set_xlabel("Exposure (%)")
#     ax_exp.legend(fontsize=8, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.25), ncol=2)

#     ax_stress = fig.add_subplot(gs[2, 1])
#     im = ax_stress.pcolormesh(equity_shocks * 100, rate_shocks_bps, stress_grid * 100,
#                             cmap="YlOrRd_r", shading="gouraud")
#     cbar = fig.colorbar(im, ax=ax_stress, fraction=0.046, pad=0.04)
#     cbar.set_label("Portfolio Impact (%)", fontsize=10)
#     cbar.ax.tick_params(labelsize=9)

#     equity_only_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 0)), np.argmin(np.abs(equity_shocks - (-0.15)))]
#     ax_stress.plot(-15, 0, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5)
#     ax_stress.annotate(f"Equity Selloff\n{equity_only_value:.2%}", (-15, 0), textcoords="offset points", xytext=(0, 8), fontsize=7, ha="center")

#     rate_only_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - 0))]
#     ax_stress.plot(0, 100, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5)
#     ax_stress.annotate(f"Rate Shock\n{rate_only_value:.2%}", (0, 100), textcoords="offset points", xytext=(-55, 3), fontsize=7, ha="left")

#     ax_stress.plot(-15, 100, marker="*", color="gold", markeredgecolor="black", markersize=13, zorder=5)
#     combined_value = stress_grid[np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - (-0.15)))]
#     ax_stress.annotate(f"Combined\n{combined_value:.2%}", (-15, 100), textcoords="offset points", xytext=(8, 3), fontsize=7, fontweight="bold")

#     ax_stress.set_xlim(-25, 2)
#     ax_stress.set_ylim(-5, 210)
#     ax_stress.set_xlabel("Equity Shock (%)")
#     ax_stress.set_ylabel("Rate Shock (bps)")
#     ax_stress.set_title("Stress Sensitivity Surface")

#     return fig


def build_dashboard_page(
    portfolio_returns: pd.Series,
    weights: pd.DataFrame,
    equity_shocks,
    rate_shocks_bps,
    stress_grid,
    exposure_dimension: str = "Asset Type",
    contribution: pd.DataFrame | None = None,
    currency_legs: pd.DataFrame | None = None,
    fx_by_currency: pd.DataFrame | None = None,
) -> plt.Figure:
    """
    Assemble the full single-page risk dashboard.

    Layout is a KPI summary strip over three rows:

        cumulative wealth        |  drawdown from peak
        exposure by dimension    |  return contribution by dimension
        stress sensitivity surface (full width)

    Exposure and contribution sit side by side, share the same dimension
    selector and are ordered identically, so a row reads across: how much of
    the book a bucket is, and what it contributed to the return.

    Args:
        portfolio_returns (pd.Series): daily portfolio returns.
        weights (pd.DataFrame): PortfolioWeights sheet. Must carry the column
            named in `exposure_dimension`.
        equity_shocks (array-like): equity shock grid values used to build
            stress_grid (needed here only for axis labeling).
        rate_shocks_bps (array-like): rate shock grid values used to build
            stress_grid (needed here only for axis labeling).
        stress_grid (np.ndarray): output of compute_stress_surface(), computed
            once outside this function since it does not depend on
            portfolio_returns or exposure_dimension, and is expensive enough
            to be worth not recomputing on every date-range or
            exposure-dimension change.
        exposure_dimension (str): which dimension to break down by. 'Asset
            Type', 'Sector', 'Country', 'Rating' or 'Currency'.
        contribution (pd.DataFrame | None): daily contribution of each bucket of
            that dimension, filtered to the same date range as
            portfolio_returns. Contributions are arithmetic: exact within a
            day, and summing to the arithmetic period return rather than the
            compounded one.

    Returns:
        matplotlib.figure.Figure
    """
    kpis = build_kpi_summary(portfolio_returns)
    clean_returns = portfolio_returns.dropna()
    wealth = (1 + clean_returns).cumprod()
    running_max = wealth.cummax()
    drawdown = (wealth - running_max) / running_max

    fig = plt.figure(figsize=(12, 9.5))
    gs = gridspec.GridSpec(
        4,
        2,
        height_ratios=[0.32, 1, 1, 1],
        hspace=0.65,
        wspace=0.28,
        left=0.07,
        right=0.95,
        top=0.945,
        bottom=0.05,
    )

    fig.suptitle(
        "Portfolio Risk Dashboard",
        fontsize=13,
        fontweight="bold",
        x=0.07,
        ha="left",
        color=PALETTE["text_dark"],
        y=0.985,
    )

    ax_kpi = fig.add_subplot(gs[0, :])
    ax_kpi.axis("off")
    _draw_kpi_cards(ax_kpi, kpis)

    ax_wealth = fig.add_subplot(gs[1, 0])
    ax_wealth.plot(wealth.index, wealth.values, color=PALETTE["primary"], linewidth=1.3)
    ax_wealth.set_title("Cumulative Wealth")
    ax_wealth.set_ylabel("Wealth (growth of $1)")
    ax_wealth.xaxis.set_major_locator(mticker.MaxNLocator(5))
    ax_wealth.tick_params(axis="x", labelsize=9)
    plt.setp(ax_wealth.get_xticklabels(), rotation=20, ha="right")

    ax_dd = fig.add_subplot(gs[1, 1])
    ax_dd.fill_between(
        drawdown.index, drawdown.to_numpy() * 100, 0, color=PALETTE["loss"], alpha=0.55
    )
    ax_dd.set_title("Drawdown from Peak")
    ax_dd.set_ylabel("Drawdown (%)")
    ax_dd.yaxis.set_major_formatter(mticker.PercentFormatter())
    ax_dd.tick_params(axis="x", labelsize=9)
    ax_dd.xaxis.set_major_locator(mticker.MaxNLocator(5))
    plt.setp(ax_dd.get_xticklabels(), rotation=20, ha="right")

    # Exposure is built first so the contribution panel beside it can be ordered
    # to match; otherwise the two panels sort differently and a row cannot be
    # read across.
    ax_exp = fig.add_subplot(gs[2, 0])
    exp_data = breakdown_exposure(weights, exposure_dimension)
    y_pos = range(len(exp_data))
    ax_exp.barh(
        y_pos, exp_data["gross_exposure"] * 100, color=PALETTE["gross"], height=0.62, label="Gross"
    )
    ax_exp.barh(
        y_pos, exp_data["net_exposure"] * 100, color=PALETTE["primary"], height=0.3, label="Net"
    )
    ax_exp.set_yticks(list(y_pos))
    ax_exp.set_yticklabels(exp_data.index, fontsize=8.5)
    ax_exp.invert_yaxis()
    ax_exp.set_title(f"Exposure by {exposure_dimension}")
    ax_exp.set_xlabel("Exposure (% of NAV)")
    ax_exp.grid(axis="y", visible=False)
    ax_exp.legend(fontsize=8, loc="lower right", frameon=True, framealpha=0.92, edgecolor="none")

    ax_con = fig.add_subplot(gs[2, 1])
    ax_con.set_title(f"Return Contribution by {exposure_dimension}")
    ax_con.grid(axis="y", visible=False)
    if contribution is not None and not contribution.empty:
        totals = contribution.sum().reindex(exp_data.index).fillna(0.0) * 100
        y_pos = range(len(totals))
        colours = [PALETTE["loss"] if value < 0 else PALETTE["gain"] for value in totals]
        ax_con.barh(y_pos, totals.values, color=colours, height=0.6)
        ax_con.set_yticks(list(y_pos))
        ax_con.set_yticklabels(totals.index, fontsize=8.5)
        ax_con.invert_yaxis()
        ax_con.axvline(0, color=PALETTE["text_dark"], linewidth=0.9)

        for i, value in enumerate(totals.values):
            ax_con.annotate(
                f"{value:+.1f} pp",
                xy=(value, i),
                xytext=(-6 if value < 0 else 6, 0),
                textcoords="offset points",
                va="center",
                ha="right" if value < 0 else "left",
                fontsize=9,
                color=PALETTE["text_dark"],
            )

        # Room for the value labels so they never clip at either end.
        span = max(abs(totals.min()), abs(totals.max())) or 1.0
        ax_con.set_xlim(min(totals.min(), 0) - span * 0.55, max(totals.max(), 0) + span * 0.55)
        ax_con.set_xlabel("Contribution to portfolio return (pp, arithmetic)")
    else:
        ax_con.text(
            0.5,
            0.5,
            "no contribution data supplied",
            transform=ax_con.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=PALETTE["text_muted"],
        )
        ax_con.set_xticks([])
        ax_con.set_yticks([])
        ax_con.grid(visible=False)

    ax_bridge = fig.add_subplot(gs[3, 0])
    if currency_legs is not None and fx_by_currency is not None:
        _draw_return_bridge(ax_bridge, currency_legs, fx_by_currency, portfolio_returns)
    else:
        ax_bridge.set_title("From Local Return to USD Return")
        ax_bridge.text(
            0.5,
            0.5,
            "no currency decomposition supplied",
            transform=ax_bridge.transAxes,
            ha="center",
            va="center",
            fontsize=9,
            color=PALETTE["text_muted"],
        )
        ax_bridge.set_xticks([])
        ax_bridge.set_yticks([])
        ax_bridge.grid(visible=False)

    ax_stress = fig.add_subplot(gs[3, 1])
    equity_shocks = np.asarray(equity_shocks)
    rate_shocks_bps = np.asarray(rate_shocks_bps)
    im = ax_stress.pcolormesh(
        equity_shocks * 100, rate_shocks_bps, stress_grid * 100, cmap="YlOrRd_r", shading="gouraud"
    )
    cbar = fig.colorbar(im, ax=ax_stress, fraction=0.046, pad=0.04)
    cbar.set_label("Portfolio Impact (%)", fontsize=10)
    cbar.ax.tick_params(labelsize=9)

    equity_only_value = stress_grid[
        np.argmin(np.abs(rate_shocks_bps - 0)), np.argmin(np.abs(equity_shocks - (-0.15)))
    ]
    ax_stress.plot(
        -15, 0, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5
    )
    ax_stress.annotate(
        f"Equity Selloff\n{equity_only_value:.2%}",
        (-15, 0),
        textcoords="offset points",
        xytext=(0, 8),
        fontsize=9,
        ha="center",
    )

    rate_only_value = stress_grid[
        np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - 0))
    ]
    ax_stress.plot(
        0, 100, marker="D", color="white", markeredgecolor="black", markersize=8, zorder=5
    )
    ax_stress.annotate(
        f"Rate Shock\n{rate_only_value:.2%}",
        (0, 100),
        textcoords="offset points",
        xytext=(-55, 3),
        fontsize=9,
        ha="left",
    )

    ax_stress.plot(
        -15, 100, marker="*", color="gold", markeredgecolor="black", markersize=13, zorder=5
    )
    combined_value = stress_grid[
        np.argmin(np.abs(rate_shocks_bps - 100)), np.argmin(np.abs(equity_shocks - (-0.15)))
    ]
    ax_stress.annotate(
        f"Combined\n{combined_value:.2%}",
        (-15, 100),
        textcoords="offset points",
        xytext=(8, 3),
        fontsize=9,
        fontweight="bold",
    )

    ax_stress.set_xlim(-25, 2)
    ax_stress.set_ylim(-5, 210)
    ax_stress.set_xlabel("Equity Shock (%)")
    ax_stress.set_ylabel("Rate Shock (bps)")
    ax_stress.set_title("Stress Sensitivity Surface")

    return fig


def _draw_return_bridge(ax, currency_legs, fx_by_currency, portfolio_returns):
    """
    Waterfall from the local-currency return to the reported USD return.

    Currency steps are the FX effect only, held in fixed alphabetical order so
    that changing the date range moves the bars' heights but never their
    positions. USD is dropped: a USD security has no FX leg by definition.

    The final step bundles the local-times-FX cross term with the gap between
    the arithmetic sum of daily returns and the compounded return, so the chart
    closes exactly on the figure shown in the KPI strip rather than on the
    arithmetic total.
    """
    local = currency_legs["local"].sum() * 100
    cross = currency_legs["cross"].sum() * 100
    fx_steps = (fx_by_currency.sum() * 100).drop("USD", errors="ignore").sort_index()

    arithmetic = local + fx_steps.sum() + cross
    total = calculate_cumulative_return(portfolio_returns) * 100
    compounding = total - arithmetic + cross

    steps = list(fx_steps.values) + [compounding]
    labels = ["Local"] + list(fx_steps.index) + ["Compound", "USD"]

    # Running level after each bar, used for the floating bars and the connectors.
    levels = [local]
    for value in steps:
        levels.append(levels[-1] + value)

    ax.bar(0, local, width=0.62, color=PALETTE["primary"])
    for i, value in enumerate(steps, start=1):
        bottom = levels[i - 1] if value >= 0 else levels[i]
        colour = PALETTE["gain"] if value >= 0 else PALETTE["loss"]
        ax.bar(i, abs(value), bottom=bottom, width=0.62, color=colour)
    ax.bar(len(labels) - 1, total, width=0.62, color=PALETTE["primary"])

    for i, level in enumerate(levels):
        ax.plot(
            [i + 0.31, i + 1 - 0.31],
            [level, level],
            color=PALETTE["text_muted"],
            linewidth=0.8,
            linestyle=(0, (3, 3)),
        )

    values = [local] + steps + [total]
    for i, value in enumerate(values):
        top = value if i in (0, len(values) - 1) else max(levels[i - 1], levels[i])
        bottom = 0 if i in (0, len(values) - 1) else min(levels[i - 1], levels[i])
        anchor = top if value >= 0 or i in (0, len(values) - 1) else bottom
        ax.annotate(
            f"{value:+.2f}",
            xy=(i, anchor),
            xytext=(0, 4 if anchor >= 0 else -11),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color=PALETTE["text_dark"],
        )

    ax.axhline(0, color=PALETTE["text_dark"], linewidth=0.9)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, fontsize=8.5, rotation=20, ha="right")
    ax.set_title("From Local Return to USD Return")
    ax.set_ylabel("Portfolio return (pp)")
    ax.set_xlabel("Currency steps are the FX effect only")
    ax.grid(axis="x", visible=False)
    low = min([0, local, total] + levels)
    high = max([0, local, total] + levels)
    span = (high - low) or 1.0
    ax.set_ylim(low - span * 0.30, high + span * 0.12)
