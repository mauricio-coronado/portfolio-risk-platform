import pandas as pd
import pytest

from riskplatform.exposure import reconcile_exposure, breakdown_exposure


def test_reconcile_exposure_matches_stated_values():
    """A small synthetic example with an embedded answer key,
    matching the real PortfolioWeights sheet's convention, should
    pass without raising."""
    weights = pd.DataFrame({
        'Ticker': ['A', 'B', 'C'],
        'Weight': [0.6, 0.5, -0.1],
        'Exposure check': ['Net', 'Gross', 'Short'],
        'Value': [1.0, 1.2, -0.1],
    })

    result = reconcile_exposure(weights)

    assert result['net'] == pytest.approx(1.0)
    assert result['gross'] == pytest.approx(1.2)
    assert result['short'] == pytest.approx(-0.1)
    assert result['long'] == pytest.approx(1.1)


def test_reconcile_exposure_raises_on_mismatch():
    """If the stated answer key disagrees with the computed value
    beyond tolerance, this should fail loudly."""
    weights = pd.DataFrame({
        'Ticker': ['A', 'B', 'C'],
        'Weight': [0.6, 0.5, -0.1],
        'Exposure check': ['Net', 'Gross', 'Short'],
        'Value': [2.0, 1.2, -0.1],  # Net should be 1.0, not 2.0
    })

    with pytest.raises(ValueError):
        reconcile_exposure(weights)


def test_breakdown_exposure_includes_nr_rating():
    """NR is a legitimate rating category (all Equities are NR) and
    must appear as its own row, not be dropped."""
    weights = pd.DataFrame({
        'Ticker': ['A', 'B'],
        'Weight': [0.5, 0.5],
        'Rating': ['NR', 'AA'],
    })

    result = breakdown_exposure(weights, 'Rating')

    assert 'NR' in result.index
    assert result.loc['NR', 'net_exposure'] == pytest.approx(0.5)