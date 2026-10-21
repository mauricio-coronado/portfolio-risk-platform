import pandas as pd
import pytest

from riskplatform.risk_metrics import (
    calculate_cumulative_return,
    calculate_expected_shortfall,
    calculate_historical_var,
    calculate_max_drawdown,
    count_var_exceptions,
)


def test_calculate_cumulative_return_compounds_not_sums():
    """+10% then -10% should compound to -1%, not sum to 0%, this is
    a core distinction between compounding vs additive."""
    returns = pd.Series([0.10, -0.10])
    result = calculate_cumulative_return(returns)
    assert result == pytest.approx(-0.01)


def test_calculate_max_drawdown_known_example():
    """+20%, +20%, -40%: wealth path 1 -> 1.2 -> 1.44 -> 0.864.
    Peak is 1.44, trough is 0.864, drawdown = (0.864-1.44)/1.44 = -0.40
    exactly."""
    returns = pd.Series([0.20, 0.20, -0.40])
    result = calculate_max_drawdown(returns)
    assert result == pytest.approx(-0.40)


def test_calculate_historical_var_known_distribution():
    """21 evenly spaced returns from -10% to +10%. With linear
    interpolation, the 5th percentile lands exactly on the 2nd
    smallest value (-9%), so VaR_95 should be exactly 9%."""
    returns = pd.Series([i / 100 for i in range(-10, 11)])
    result = calculate_historical_var(returns, confidence_level=0.95)
    assert result == pytest.approx(0.09)


def test_calculate_expected_shortfall_known_distribution():
    """Same distribution: at the 95% VaR threshold (-9%), the tail
    (values <= -9%) is exactly [-10%, -9%], averaging to -9.5%."""
    returns = pd.Series([i / 100 for i in range(-10, 11)])
    result = calculate_expected_shortfall(returns, confidence_level=0.95)
    assert result == pytest.approx(0.095)


def test_count_var_exceptions_counts_breaches_correctly():
    """Of five returns, exactly two (-8%, -5%) are worse than a 4% VaR
    threshold; the other three are not."""
    returns = pd.Series([-0.08, -0.05, -0.02, 0.01, 0.03])
    result = count_var_exceptions(returns, var_estimate=0.04)
    assert result == 2
