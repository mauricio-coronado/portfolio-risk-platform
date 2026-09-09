import pandas as pd
import numpy as np
import pytest

from src.returns import (
    calculate_security_returns,
    calculate_portfolio_returns,
    # calculate_group_cumulative_returns,
)

def test_calculate_security_returns_first_day_is_nan():
    """The first day has no prior day to compare against, so it must
    be NaN, not a fabricated value."""
    tri_usd = pd.DataFrame({
        'Date': pd.to_datetime(['2024-01-01', '2024-01-02']),
        'AAA': [100.0, 110.0],
    })

    result = calculate_security_returns(tri_usd)

    assert pd.isna(result['AAA'].iloc[0])
    assert result['AAA'].iloc[1] == pytest.approx(0.10)


def test_calculate_portfolio_returns_excludes_low_coverage_day():
    """If a day's valid data covers only a tiny fraction of gross
    weight, the portfolio return for that day should be excluded
    (NaN), not silently computed from the sliver that's present."""
    weights = pd.DataFrame({'Ticker': ['A', 'B'], 'Weight': [0.99, 0.01]})
    security_returns = pd.DataFrame(
        {'A': [0.05, np.nan], 'B': [0.02, 0.03]},
        index=pd.to_datetime(['2024-01-01', '2024-01-02']),
    )

    portfolio_return, coverage = calculate_portfolio_returns(
        security_returns, weights, warn_threshold=0.99, exclude_threshold=0.95
    )

    # Day 1: both present, full coverage, normal weighted sum
    expected_day1 = 0.99 * 0.05 + 0.01 * 0.02
    assert portfolio_return.iloc[0] == pytest.approx(expected_day1)

    # Day 2: only B (1% of gross weight) has data -> coverage = 0.01, well below 0.95
    assert coverage.iloc[1] == pytest.approx(0.01)
    assert pd.isna(portfolio_return.iloc[1])