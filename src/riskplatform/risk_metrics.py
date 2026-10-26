import numpy as np
import pandas as pd


def calculate_cumulative_return(returns: pd.Series) -> float:
    """
    Total cumulative return over the full period, from compounded
    daily returns.

    Args:
        returns (pd.Series): daily returns. NaN values are dropped
            before compounding (a NaN day contributes no return,
            rather than breaking the compounding chain).

    Returns:
        float: cumulative return over the period (e.g. 0.15 = +15%).
    """
    clean_returns = returns.dropna()
    return (1 + clean_returns).prod() - 1  # type: ignore[operator,return-value]


def calculate_annualized_volatility(returns: pd.Series, periods_per_year: int = 252) -> float:
    """
    Annualized volatility from daily returns, using the standard
    sqrt(time) scaling convention.

    Args:
        returns (pd.Series): daily returns.
        periods_per_year (int): trading days per year used for
            annualization. Default 252 (standard convention).

    Returns:
        float: annualized volatility (e.g. 0.18 = 18%).
    """
    return returns.dropna().std() * np.sqrt(periods_per_year)


def calculate_historical_var(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Historical VaR at the given confidence level, using the empirical
    percentile of the return distribution (numpy.percentile, default
    linear interpolation between closest ranks). Reported as a
    positive loss percentage.

    Args:
        returns (pd.Series): daily returns.
        confidence_level (float): e.g. 0.95 or 0.99.

    Returns:
        float: VaR as a positive loss percentage (e.g. 0.023 = a
            2.3% loss at this confidence level).
    """
    clean_returns = returns.dropna()
    percentile = (1 - confidence_level) * 100
    quantile_return = np.percentile(clean_returns, percentile)
    return -quantile_return


def calculate_expected_shortfall(returns: pd.Series, confidence_level: float = 0.95) -> float:
    """
    Expected Shortfall (Conditional VaR) at the given confidence
    level: the average return among all days worse than the VaR
    threshold. Reported as a positive loss percentage.

    Args:
        returns (pd.Series): daily returns.
        confidence_level (float): e.g. 0.95 or 0.99.

    Returns:
        float: ES as a positive loss percentage.
    """
    clean_returns = returns.dropna()
    percentile = (1 - confidence_level) * 100
    var_threshold = np.percentile(clean_returns, percentile)
    tail_returns = clean_returns[clean_returns <= var_threshold]
    return -tail_returns.mean()


def calculate_tail_count(returns: pd.Series, confidence_level: float = 0.95) -> int:
    """
    Number of observations at or beyond the VaR threshold, i.e. the
    sample size behind calculate_expected_shortfall's average.
    """
    clean_returns = returns.dropna()
    percentile = (1 - confidence_level) * 100
    var_threshold = np.percentile(clean_returns, percentile)
    return int((clean_returns <= var_threshold).sum())


def calculate_max_drawdown(returns: pd.Series) -> float:
    """
    Maximum drawdown, computed from compounded wealth, not from a
    cumulative sum of returns.

    Args:
        returns (pd.Series): daily returns.

    Returns:
        float: maximum drawdown as a negative number (e.g. -0.12 =
            a 12% peak-to-trough decline).
    """
    clean_returns = returns.dropna()
    wealth = (1 + clean_returns).cumprod()
    running_max = wealth.cummax()
    drawdown = (wealth - running_max) / running_max
    return drawdown.min()


def count_var_exceptions(returns: pd.Series, var_estimate: float) -> int:
    """
    In-sample VaR backtest: number of days the actual return breached
    the stated VaR threshold (loss worse than the VaR estimate).
    """
    clean_returns = returns.dropna()
    return int((clean_returns < -var_estimate).sum())


def compare_loan_pricing_frequency(
    tri_local: pd.DataFrame, security_master: pd.DataFrame, weights: pd.DataFrame
) -> dict:
    """
    Checks whether Loan securities' weekly repricing (SecurityMaster's
    Pricing Frequency) understates volatility when treated as a daily
    series, by comparing naive daily-frequency vol against a properly
    resampled weekly estimate, plus how often the whole loan sleeve is
    simultaneously stale.
    """
    loans = security_master.loc[security_master["Pricing Frequency"] == "Weekly", "Ticker"]
    loan_returns = tri_local.set_index("Date")[loans].pct_change(fill_method=None)

    daily_vol = loan_returns.std() * (252**0.5)
    weekly_returns = (1 + loan_returns).resample("W").prod() - 1
    weekly_vol = weekly_returns.std() * (52**0.5)

    loan_weights = weights.set_index("Ticker")["Weight"][loans]
    sub_portfolio = loan_returns.mul(loan_weights, axis=1).sum(axis=1) / loan_weights.sum()
    stale_day_fraction = (sub_portfolio.abs() < 1e-12).mean()

    return {
        "median_daily_scaled_vol": daily_vol.median(),
        "median_weekly_scaled_vol": weekly_vol.median(),
        "sub_portfolio_stale_day_fraction": stale_day_fraction,
    }
