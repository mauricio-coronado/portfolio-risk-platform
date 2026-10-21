import pandas as pd

def reconcile_exposure(weights: pd.DataFrame, tolerance: float = 1e-6) -> dict:
    """
    Calculate net, gross, and short exposure from signed portfolio
    weights, and reconcile them against the embedded validation
    values present in the first rows of PortfolioWeights, raising
    if they disagree beyond tolerance.

    Args:
        weights (pd.DataFrame): PortfolioWeights sheet. Must contain
            a 'Weight' column, and optionally 'Exposure check' /
            'Value' columns holding independently-stated Net/Gross/
            Short figures to reconcile against.
        tolerance (float): maximum allowed absolute difference
            between computed and stated values. Default 1e-6.

    Returns:
        dict: with keys 'net', 'gross', 'short', 'long'.

    Raises:
        ValueError: if a computed value disagrees with its stated
            counterpart beyond tolerance.
    """
    net_exposure = weights['Weight'].sum()
    gross_exposure = weights['Weight'].abs().sum()
    short_exposure = weights.loc[weights['Weight'] < 0, 'Weight'].sum()
    long_exposure = weights.loc[weights['Weight'] > 0, 'Weight'].sum()

    computed = {'Net': net_exposure, 'Gross': gross_exposure, 'Short': short_exposure}

    if 'Exposure check' in weights.columns:
        stated = weights.set_index('Exposure check')['Value'].dropna().to_dict()
        for label, computed_value in computed.items():
            if label in stated and abs(computed_value - stated[label]) > tolerance:
                raise ValueError(
                    f"{label} exposure mismatch: computed {computed_value:.4f}, "
                    f"stated {stated[label]:.4f}"
                )

    return {'net': net_exposure, 'gross': gross_exposure, 'short': short_exposure, 'long': long_exposure}


def breakdown_exposure(weights: pd.DataFrame, by: str) -> pd.DataFrame:
    """
    Break down net and gross exposure by a chosen SecurityMaster
    dimension (Asset Type, Sector, Country, or Rating).

    Divergence (gross - |net|) quantifies the gap between net and
    gross, flagging where net alone might give a misleading
    interpretation of exposure.

    Args:
        weights (pd.DataFrame): PortfolioWeights sheet. Must contain
            'Weight' and the column named in `by`.
        by (str): column to group by, e.g. 'Asset Type', 'Sector',
            'Country', or 'Rating'.

    Returns:
        pd.DataFrame: indexed by the chosen dimension, columns
            'net_exposure', 'gross_exposure', 'divergence', sorted
            by divergence descending.
    """
    working = weights.copy()
    working['abs_weight'] = working['Weight'].abs()
    grouped = working.groupby(by).agg(
        net_exposure=('Weight', 'sum'),
        gross_exposure=('abs_weight', 'sum')
    )
    grouped['divergence'] = grouped['gross_exposure'] - grouped['net_exposure'].abs()
    return grouped.sort_values('divergence', ascending=False)


def contribution_by_dimension(security_returns, weights, security_master, by):
    """Daily contribution of each bucket to the portfolio return. Contributions
    are weighted security returns summed within a bucket, so across buckets they
    add to the daily portfolio return exactly."""
    weight_series = weights.set_index('Ticker')['Weight']
    tickers = weight_series.index
    group = security_master.set_index('Ticker')[by].reindex(tickers)
    weighted = security_returns[tickers].mul(weight_series, axis=1)
    return weighted.T.groupby(group).sum().T