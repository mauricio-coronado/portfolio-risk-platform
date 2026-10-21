import numpy as np
import pandas as pd


def calculate_equity_selloff_impact(
    security_master: pd.DataFrame, market_shock: float = -0.15
) -> pd.Series:
    """
    Per-security return impact under the Equity selloff scenario:
    security return = beta x market shock. Non-Equity securities
    get an impact of 0.

    Args:
        security_master (pd.DataFrame): SecurityMaster sheet. Must
            contain 'Ticker', 'Asset Type', and 'Equity Beta'.
        market_shock (float): market-wide shock applied to equities.
            Default -0.15 (the required scenario shock).

    Returns:
        pd.Series: return impact per ticker, indexed by Ticker.

    Raises:
        ValueError: if any Equity security is missing Equity Beta.
    """
    impact = pd.Series(0.0, index=security_master["Ticker"])
    security_master = security_master.set_index("Ticker")

    equity_tickers = security_master[security_master["Asset Type"] == "Equity"].index
    beta = security_master.loc[equity_tickers, "Equity Beta"]

    if beta.isna().any():
        missing = equity_tickers[beta.isna()]
        raise ValueError(f"Missing Equity Beta for in-scope securities: {list(missing)}")

    impact.loc[equity_tickers] = beta * market_shock
    return impact


def calculate_rate_shock_impact(security_master: pd.DataFrame, delta_y: float = 0.01) -> pd.Series:
    """
    Per-security return impact under the Rate shock scenario:
    -Duration * Δy + 0.5 * Convexity * Δy², applied to Bond and Loan
    only. Non-fixed-income securities get an impact of 0.

    Args:
        security_master (pd.DataFrame): SecurityMaster sheet. Must
            contain 'Ticker', 'Asset Type', 'Effective Duration',
            and 'Convexity'.
        delta_y (float): interest rate shock size. Default 0.01
            (+100 bps, the required scenario shock).

    Returns:
        pd.Series: return impact per ticker, indexed by Ticker.

    Raises:
        ValueError: if any Bond or Loan security is missing
            Effective Duration or Convexity.
    """
    impact = pd.Series(0.0, index=security_master["Ticker"])
    security_master = security_master.set_index("Ticker")

    fixed_income_tickers = security_master[
        security_master["Asset Type"].isin(["Bond", "Loan"])
    ].index
    duration = security_master.loc[fixed_income_tickers, "Effective Duration"]
    convexity = security_master.loc[fixed_income_tickers, "Convexity"]

    if duration.isna().any() or convexity.isna().any():
        missing = fixed_income_tickers[duration.isna() | convexity.isna()]
        raise ValueError(f"Missing Duration/Convexity for in-scope securities: {list(missing)}")

    impact.loc[fixed_income_tickers] = -duration * delta_y + 0.5 * convexity * delta_y**2
    return impact


def calculate_combined_impact(equity_impact: pd.Series, rate_impact: pd.Series) -> pd.Series:
    """
    Combined per-security impact: sum of Equity selloff and Rate
    shock impacts, with no diversification offset applied, per the
    stress scenario instructions (a security's total impact is the
    sum of whichever scenario(s) apply to it, not a
    correlation-adjusted blend).

    Args:
        equity_impact (pd.Series): output of calculate_equity_selloff_impact().
        rate_impact (pd.Series): output of calculate_rate_shock_impact().

    Returns:
        pd.Series: combined return impact per ticker.
    """
    return equity_impact.add(rate_impact, fill_value=0)


def calculate_portfolio_stress_impact(security_impact: pd.Series, weights: pd.DataFrame) -> float:
    """
    Aggregate a per-security stress impact to the portfolio level,
    using signed net weights, per the stress scenario instructions.

    Args:
        security_impact (pd.Series): per-security return impact,
            indexed by Ticker (output of a scenario impact function).
        weights (pd.DataFrame): PortfolioWeights sheet. Must contain
            'Ticker' and 'Weight'.

    Returns:
        float: portfolio-level return impact under the scenario.
        Raises:
        ValueError: if any ticker in weights has no corresponding
            entry in security_impact (a genuine ticker mismatch, not
            a security correctly out of scope for the scenario, which
            already carries an impact of 0.0, not NaN).
    """
    weight_series = weights.set_index("Ticker")["Weight"]
    aligned_impact = security_impact.reindex(weight_series.index)

    if aligned_impact.isna().any():
        missing = aligned_impact[aligned_impact.isna()].index
        raise ValueError(f"No stress impact found for ticker(s): {list(missing)}")

    return (aligned_impact * weight_series).sum()


def compute_stress_surface(
    security_master: pd.DataFrame, weights: pd.DataFrame, equity_shocks, rate_shocks_bps
):
    """
    Portfolio impact across a grid of equity shock and rate shock
    magnitudes, reusing calculate_equity_selloff_impact() and
    calculate_rate_shock_impact() at each combination. Including 0%
    equity shock and 0bps rate shock in the grids means the required
    single-shock scenarios (Equity Selloff, Rate Shock) and the
    Combined scenario are all specific points inside this same
    surface, not separately computed, nothing is lost by generalizing
    beyond the three named scenarios.

    Args:
        security_master (pd.DataFrame): SecurityMaster sheet.
        weights (pd.DataFrame): PortfolioWeights sheet.
        equity_shocks (array-like): equity shock magnitudes to test,
            as decimals (e.g. -0.15 for -15%). Include 0.0 to recover
            the Rate Shock-only scenario.
        rate_shocks_bps (array-like): rate shock magnitudes to test,
            in basis points (e.g. 100 for +100bps). Include 0 to
            recover the Equity Selloff-only scenario.

    Returns:
        np.ndarray: 2D grid of shape (len(rate_shocks_bps),
            len(equity_shocks)), portfolio impact at each combination.
    """
    grid = np.zeros((len(rate_shocks_bps), len(equity_shocks)))
    for i, rate_bps in enumerate(rate_shocks_bps):
        for j, eq_shock in enumerate(equity_shocks):
            equity_impact_sec = calculate_equity_selloff_impact(
                security_master, market_shock=eq_shock
            )
            rate_impact_sec = calculate_rate_shock_impact(security_master, delta_y=rate_bps / 10000)
            combined_sec = calculate_combined_impact(equity_impact_sec, rate_impact_sec)
            grid[i, j] = calculate_portfolio_stress_impact(combined_sec, weights)
    return grid
