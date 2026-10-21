import pandas as pd

from riskplatform.risk_metrics import (
    calculate_annualized_volatility,
    calculate_cumulative_return,
    calculate_expected_shortfall,
    calculate_historical_var,
    calculate_max_drawdown,
    calculate_tail_count,
)


def build_kpi_summary(portfolio_returns: pd.Series) -> dict:
    """
    Assemble the headline metrics.

    Args:
        portfolio_returns (pd.Series): daily portfolio returns.

    Returns:
        dict: metric name -> value.
    """
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