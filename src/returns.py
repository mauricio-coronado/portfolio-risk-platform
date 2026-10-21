import pandas as pd
import numpy as np

def calculate_security_returns(total_return_index_usd: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate daily simple returns per security from the USD-converted
    total return index.

    No forward-fill is applied: pandas' pct_change() naturally produces
    NaN across a gap in the underlying data rather than fabricating a
    value, consistent with the no-forward-fill policy for this exercise.

    Args:
        total_return_index_usd (pd.DataFrame): output of convert_to_usd().
            'Date' column plus one column per ticker, in USD.

    Returns:
        pd.DataFrame: daily returns, indexed by Date, one column per
            ticker. First row is NaN for every ticker (no prior day to
            compare against).
    """
    return total_return_index_usd.set_index('Date').pct_change(fill_method=None)


def calculate_portfolio_returns(security_returns: pd.DataFrame, weights: pd.DataFrame,
                                  warn_threshold: float = 0.99,
                                  exclude_threshold: float = 0.95) -> tuple[pd.Series, pd.Series]:
    """
    Calculate daily portfolio returns as the weighted sum of security
    returns, using signed net weights. A security with no return that
    day is simply excluded from the sum (skipna=True), so coverage
    (share of gross weight backed by valid data) is tracked alongside
    the return, and thresholds flag or exclude days where too much of
    the portfolio is missing to trust the result.

    Args:
        security_returns (pd.DataFrame): output of
            calculate_security_returns(). Daily returns indexed by
            Date, one column per ticker.
        weights (pd.DataFrame): PortfolioWeights sheet. Must contain
            'Ticker' and 'Weight' columns (signed, net NAV weights).
        warn_threshold (float): coverage below this triggers a
            warning but the day is still included. Default 0.99.
        exclude_threshold (float): coverage below this excludes the
            day's return entirely. Default 0.95.

    Returns:
        tuple[pd.Series, pd.Series]:
            portfolio_return: daily portfolio return, indexed by Date.
            coverage: daily share (0-1) of gross weight backed by
                valid data, indexed by Date.
    """
    weight_series = weights.set_index('Ticker')['Weight']
    gross_weight_total = weight_series.abs().sum()

    aligned_returns = security_returns[weight_series.index]
    valid_mask = aligned_returns.notna()

    covered_gross_weight = valid_mask.multiply(weight_series.abs(), axis=1).sum(axis=1)
    coverage = covered_gross_weight / gross_weight_total

    weighted = aligned_returns.multiply(weight_series, axis=1)
    portfolio_return = weighted.sum(axis=1, skipna=True)

    warn_days = coverage[(coverage < warn_threshold) & (coverage >= exclude_threshold)]
    exclude_days = coverage[coverage < exclude_threshold]

    if not warn_days.empty:
        print(f"WARNING: {len(warn_days)} day(s) between {exclude_threshold:.0%}-{warn_threshold:.0%} "
              f"coverage, included but flagged for review:")
        print(warn_days)

    if not exclude_days.empty:
        print(f"EXCLUDED: {len(exclude_days)} day(s) below {exclude_threshold:.0%} coverage, "
              f"return set to NaN:")
        print(exclude_days)
        portfolio_return.loc[exclude_days.index] = np.nan

    return portfolio_return, coverage


def calculate_fx_returns(fx: pd.DataFrame, ticker_currency: pd.Series,
                         columns: pd.Index) -> pd.DataFrame:
    """
    Daily FX return per security: the change in USD value of one unit of that
    security's local currency.

    FX_Local_per_USD is quoted as local units per USD 1, so a unit of local
    currency is worth 1/fx in USD and its return is fx_(t-1)/fx_t - 1. A
    weakening local currency therefore produces a negative FX return.

    Args:
        fx (pd.DataFrame): FX_Local_per_USD sheet, 'Date' plus one column per currency.
        ticker_currency (pd.Series): ticker -> currency code.
        columns (pd.Index): security tickers, in the order to return them.

    Returns:
        pd.DataFrame: daily FX return, indexed by Date, one column per ticker.
    """
    fx_indexed = fx.set_index('Date')
    fx_returns = fx_indexed.shift(1) / fx_indexed - 1

    per_ticker = fx_returns[ticker_currency.reindex(columns).values].copy()
    per_ticker.columns = columns
    return per_ticker


def decompose_currency(security_returns_local: pd.DataFrame, fx_returns: pd.DataFrame,
                       weights: pd.DataFrame) -> pd.DataFrame:
    """
    Split the daily portfolio return into a local leg, an FX leg and a cross term.

    For any security the USD return decomposes exactly:

        (1 + r_usd) = (1 + r_local)(1 + r_fx)
        r_usd       = r_local + r_fx + r_local * r_fx

    The cross term is the interaction: the FX move applies to the grown asset,
    not the starting one. It is small daily but not zero, and including it is
    what makes the decomposition exact rather than approximate.

    The FX leg is masked to securities that actually have a return that day. An
    FX rate exists even where a security's price is missing, and counting FX on
    a position with no return would put the currency leg on a different book
    than the local leg, so the legs would stop reconciling.

    Args:
        security_returns_local (pd.DataFrame): daily local-currency security returns.
        fx_returns (pd.DataFrame): output of calculate_fx_returns().
        weights (pd.DataFrame): PortfolioWeights sheet.

    Returns:
        pd.DataFrame: indexed by Date, columns ['local', 'fx', 'cross'], summing
            to the daily USD portfolio return.
    """
    weight_series = weights.set_index('Ticker')['Weight']
    tickers = weight_series.index

    local = security_returns_local[tickers]
    fx_valid = fx_returns[tickers].where(local.notna())

    return pd.DataFrame({
        'local': local.mul(weight_series, axis=1).sum(axis=1, skipna=True),
        'fx': fx_valid.mul(weight_series, axis=1).sum(axis=1, skipna=True),
        'cross': (local * fx_valid).mul(weight_series, axis=1).sum(axis=1, skipna=True),
    })


def fx_contribution_by_currency(security_returns_local: pd.DataFrame,
                                fx_returns: pd.DataFrame, weights: pd.DataFrame,
                                ticker_currency: pd.Series) -> pd.DataFrame:
    """
    Daily FX contribution attributed to each currency. Columns sum to the 'fx'
    column of decompose_currency().

    Args:
        security_returns_local (pd.DataFrame): daily local-currency security
            returns, used only to mask FX to days a security actually traded.
        fx_returns (pd.DataFrame): output of calculate_fx_returns().
        weights (pd.DataFrame): PortfolioWeights sheet.
        ticker_currency (pd.Series): ticker -> currency code.

    Returns:
        pd.DataFrame: indexed by Date, one column per currency.
    """
    weight_series = weights.set_index('Ticker')['Weight']
    tickers = weight_series.index
    currency_of = ticker_currency.reindex(tickers)

    valid = security_returns_local[tickers].notna()
    weighted_fx = fx_returns[tickers].where(valid).mul(weight_series, axis=1)
    return weighted_fx.T.groupby(currency_of).sum().T