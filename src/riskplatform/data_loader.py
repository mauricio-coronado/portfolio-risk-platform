from pathlib import Path

import pandas as pd

DEFAULT_DATA_PATH = Path("data") / "portfolio.xlsx"
SHEETS = [
    "SecurityMaster",
    "PortfolioWeights",
    "TotalReturnIndex_Local",
    "RawPrice_Local",
    "FX_Local_per_USD",
    "CorporateActions",
    "StressScenarios",
]


def load_inputs(path: str | Path | None = None) -> dict:
    """
    Load all input sheets from the workbook.

    Args:
        path (str | Path | None): workbook location. Defaults to
            DEFAULT_DATA_PATH, resolved against the working directory.

    Returns:
        dict[str, pd.DataFrame]: one DataFrame per sheet, keyed by sheet name
            (see SHEETS for the exact keys).
    """
    return pd.read_excel(path or DEFAULT_DATA_PATH, sheet_name=SHEETS)


def validate_inputs(data: dict) -> None:
    """
    Structural checks on the raw loaded data, run immediately after
    loading and before any calculation begins. These are hard
    failures: if any of these don't hold, the data isn't safe to
    proceed on at all.

    Args:
        data (dict): output of load_inputs().

    Raises:
        ValueError: if tickers are inconsistent across SecurityMaster,
            PortfolioWeights, and TotalReturnIndex_Local; if
            SecurityMaster has missing required fields; if
            PortfolioWeights don't sum to 1.0; or if
            TotalReturnIndex_Local and RawPrice_Local disagree on a
            date not explained by a documented corporate action.
    """
    sm = data["SecurityMaster"]
    weights = data["PortfolioWeights"]
    tri = data["TotalReturnIndex_Local"]

    sm_tickers = set(sm["Ticker"])
    weight_tickers = set(weights["Ticker"])
    tri_tickers = set(tri.columns) - {"Date"}

    # No duplicated tickers.
    for name in ["SecurityMaster", "PortfolioWeights"]:
        tickers = data[name]["Ticker"]
        duplicates = sorted(tickers[tickers.duplicated()].unique())
        if duplicates:
            raise ValueError(f"{name} has duplicate tickers: {duplicates}")

    # Same tickers must appear in all three sheets
    if sm_tickers != weight_tickers:
        raise ValueError(
            f"Ticker mismatch, SecurityMaster vs PortfolioWeights: "
            f"{sm_tickers.symmetric_difference(weight_tickers)}"
        )
    if sm_tickers != tri_tickers:
        raise ValueError(
            f"Ticker mismatch, SecurityMaster vs TotalReturnIndex_Local: "
            f"{sm_tickers.symmetric_difference(tri_tickers)}"
        )

    # Core classification fields must be populated for every security
    required_fields = ["Ticker", "Asset Type", "Sector", "Country", "Rating", "Currency"]
    missing_fields = sm[required_fields].isna().sum()
    if missing_fields.any():
        raise ValueError(
            f"SecurityMaster has missing required fields:\n{missing_fields[missing_fields > 0]}"
        )

    # Portfolio weights must add up to 100% (or 1.0) across all securities
    net_weight = weights["Weight"].sum()
    if abs(net_weight - 1.0) > 1e-6:
        raise ValueError(f"PortfolioWeights net weight is {net_weight:.6f}, expected 1.0")

    # TRI and RawPrice should only diverge on documented split dates
    raw_price = data["RawPrice_Local"]
    corporate_actions = data["CorporateActions"]

    tri_returns = tri.set_index("Date").pct_change(fill_method=None)
    raw_returns = raw_price.set_index("Date").pct_change(fill_method=None)
    common_tickers = [c for c in tri_returns.columns if c in raw_returns.columns]

    diff = (tri_returns[common_tickers] - raw_returns[common_tickers]).abs()
    diff_long = diff.stack()
    discrepancies = diff_long[diff_long > 1e-6]

    if not discrepancies.empty:
        flagged_dates = set(d for d, t in discrepancies.index)
        known_split_dates = set(pd.to_datetime(corporate_actions["Effective Date"]))
        unexplained_dates = flagged_dates - known_split_dates
        if unexplained_dates:
            raise ValueError(
                f"TotalReturnIndex_Local and RawPrice_Local disagree on dates not "
                f"explained by CorporateActions: {sorted(unexplained_dates)}"
            )


def summarize_missing_data(total_return_index_local: pd.DataFrame) -> pd.DataFrame:
    """
    Report every missing value in TotalReturnIndex_Local, by ticker
    and date.

    Purely descriptive, does not raise. A small number of missing
    values is expected and handled downstream; this function exists
    to make that gap explicit and countable up front, rather
    than only discovered incidentally wherever it happens to surface.

    Args:
        total_return_index_local (pd.DataFrame): TotalReturnIndex_Local
            sheet, 'Date' column plus one column per ticker.

    Returns:
        pd.DataFrame: one row per missing value, columns ['Date', 'Ticker'].
            Empty DataFrame if there are no missing values.
    """
    missing = total_return_index_local.set_index("Date").isna()
    missing_long = missing[missing.any(axis=1)].stack()

    assert isinstance(missing_long, pd.Series)          # narrows from here down

    missing_long = missing_long[missing_long].reset_index()
    missing_long.columns = ["Date", "Ticker", "_"]
    return missing_long[["Date", "Ticker"]]


def get_security_currencies(security_master: pd.DataFrame) -> pd.Series:
    """
    Build a security ticker -> local currency lookup from SecurityMaster.

    Args:
        security_master (pd.DataFrame): the SecurityMaster sheet, must contain
            'Ticker' and 'Currency' columns.

    Returns:
        pd.Series: local currency code (e.g. 'USD', 'EUR'), indexed by Ticker.
    """
    return security_master.set_index("Ticker")["Currency"]


def convert_to_usd(
    total_return_index_local: pd.DataFrame, fx: pd.DataFrame, ticker_currency: pd.Series
) -> pd.DataFrame:
    """
    Convert TotalReturnIndex_Local (local currency) to USD, per security,
    using each security's own currency.

    FX_Local_per_USD is quoted as local currency units per 1 USD, so a
    local value is converted to USD by dividing by the FX rate.

    FX completeness is validated explicitly here: a missing FX value
    breaks every security in that currency at once, so it's flagged
    at the source rather than surfacing later as an unexplained
    coverage drop.

    Args:
        total_return_index_local (pd.DataFrame): TotalReturnIndex_Local sheet. Must contain
            a 'Date' column plus one column per security ticker, values in
            each security's local currency.
        fx (pd.DataFrame): FX_Local_per_USD sheet. Must contain a 'Date'
            column plus one column per currency code.
        ticker_currency (pd.Series): output of get_security_currencies(),
            mapping each ticker to its local currency code.

    Returns:
        pd.DataFrame: same shape and columns as total_return_index_local, with a 'Date'
            column plus one column per ticker, values converted to USD.

    Raises:
        AssertionError: if total_return_index_local and fx do not share the same Date index.
        ValueError: if a currency in ticker_currency has no matching column in fx.
    """
    assert total_return_index_local["Date"].equals(fx["Date"]), (
        "TRI and FX date indices do not match"
    )

    fx = fx.set_index("Date")
    total_return_index_local = total_return_index_local.set_index("Date")

    used_currencies = ticker_currency.unique()
    for currency in used_currencies:
        if currency not in fx.columns:
            raise ValueError(f"No FX rate column found for currency '{currency}'")
        missing_dates = fx[currency][fx[currency].isna()].index
        if len(missing_dates) > 0:
            print(
                f"WARNING: {currency} FX rate missing on {len(missing_dates)} date(s): "
                f"{list(missing_dates)}. This will affect all {currency}-denominated securities."
            )

    # Broadcast each ticker's FX rate into its own column, mirroring
    # total_return_index_local's shape, so the two can be divided in
    # one vectorized operation instead of looping per ticker.
    currencies_per_column = ticker_currency.reindex(total_return_index_local.columns)
    fx_rates_aligned = fx[currencies_per_column.to_numpy()].copy()
    fx_rates_aligned.columns = total_return_index_local.columns

    total_return_index_usd = (total_return_index_local / fx_rates_aligned).copy()
    return total_return_index_usd.reset_index()
