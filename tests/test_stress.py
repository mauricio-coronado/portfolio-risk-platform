import pandas as pd
import pytest

from riskplatform.stress import (
    calculate_combined_impact,
    calculate_equity_selloff_impact,
    calculate_portfolio_stress_impact,
    calculate_rate_shock_impact,
)


def test_equity_selloff_impact_zero_for_non_equity():
    """Only Equity securities should carry a nonzero impact under
    this scenario."""
    security_master = pd.DataFrame({
        'Ticker': ['E1', 'B1'],
        'Asset Type': ['Equity', 'Bond'],
        'Equity Beta': [1.2, None],
    })

    result = calculate_equity_selloff_impact(security_master, market_shock=-0.15)

    assert result['E1'] == pytest.approx(1.2 * -0.15)
    assert result['B1'] == 0.0


def test_rate_shock_impact_zero_for_equity():
    """Only Bond/Loan securities should carry a nonzero impact under
    this scenario."""
    security_master = pd.DataFrame({
        'Ticker': ['E1', 'B1'],
        'Asset Type': ['Equity', 'Bond'],
        'Effective Duration': [None, 5.0],
        'Convexity': [None, 20.0],
    })

    result = calculate_rate_shock_impact(security_master, delta_y=0.01)

    assert result['E1'] == 0.0
    # -Duration*dy + 0.5*Convexity*dy^2 = -5*0.01 + 0.5*20*0.0001 = -0.049
    assert result['B1'] == pytest.approx(-0.049)


def test_combined_impact_equals_sum():
    """Combined should be the elementwise sum, no diversification
    offset applied, per the required convention."""
    equity_impact = pd.Series({'E1': -0.18, 'B1': 0.0})
    rate_impact = pd.Series({'E1': 0.0, 'B1': -0.049})

    result = calculate_combined_impact(equity_impact, rate_impact)

    assert result['E1'] == pytest.approx(-0.18)
    assert result['B1'] == pytest.approx(-0.049)


def test_portfolio_stress_impact_raises_on_ticker_mismatch():
    """A ticker present in weights but missing from the impact
    series is a genuine mismatch, not a legitimate out-of-scope
    security (those already carry 0.0, not a missing entry)."""
    security_impact = pd.Series({'E1': -0.18})  # 'B1' missing
    weights = pd.DataFrame({'Ticker': ['E1', 'B1'], 'Weight': [0.5, 0.5]})

    with pytest.raises(ValueError):
        calculate_portfolio_stress_impact(security_impact, weights)
