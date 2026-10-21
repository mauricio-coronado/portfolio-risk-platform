import pandas as pd
import pytest

from riskplatform.data_loader import convert_to_usd, summarize_missing_data, validate_inputs


def test_convert_to_usd_leaves_usd_securities_unchanged():
    """A USD-denominated security should be unchanged by conversion,
    since dividing by an FX rate of 1.0 is a no-op."""
    tri_local = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "AAA": [100.0, 105.0],
        }
    )
    fx = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "USD": [1.0, 1.0],
        }
    )
    ticker_currency = pd.Series({"AAA": "USD"})

    result = convert_to_usd(tri_local, fx, ticker_currency)

    assert result["AAA"].tolist() == [100.0, 105.0]


def test_convert_to_usd_divides_by_fx_rate():
    """FX_Local_per_USD is local currency units per USD 1, so converting to
    USD means DIVIDING by the rate, not multiplying. EUR at 0.91 per USD:
    91.00 EUR must equal exactly 100.00 USD, not 82.81 (91.0 * 0.91), which
    is the plausible-looking number the inverted convention would give."""
    tri_local = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01"]),
            "EUR1": [91.0],
        }
    )
    fx = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01"]),
            "EUR": [0.91],
        }
    )
    ticker_currency = pd.Series({"EUR1": "EUR"})

    result = convert_to_usd(tri_local, fx, ticker_currency)

    assert result["EUR1"].iloc[0] == pytest.approx(100.0)


def test_convert_to_usd_raises_for_unmapped_currency():
    """If a ticker's currency has no matching column in the FX sheet,
    this should fail loudly, not silently produce NaN."""
    tri_local = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01"]),
            "AAA": [100.0],
        }
    )
    fx = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01"]),
            "USD": [1.0],
        }
    )
    ticker_currency = pd.Series({"AAA": "XYZ"})

    with pytest.raises(ValueError):
        convert_to_usd(tri_local, fx, ticker_currency)


def test_validate_inputs_raises_on_duplicate_ticker():
    """A ticker repeated within SecurityMaster should be caught explicitly"""
    data = {
        "SecurityMaster": pd.DataFrame(
            {
                "Ticker": ["A", "A", "B"],
                "Asset Type": ["Equity", "Equity", "Bond"],
                "Sector": ["Tech", "Tech", "Financials"],
                "Country": ["United States", "United States", "United States"],
                "Rating": ["NR", "NR", "AA"],
                "Currency": ["USD", "USD", "USD"],
            }
        ),
        "PortfolioWeights": pd.DataFrame(
            {
                "Ticker": ["A", "B"],
                "Weight": [0.5, 0.5],
            }
        ),
        "TotalReturnIndex_Local": pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "A": [100.0],
                "B": [100.0],
            }
        ),
    }

    with pytest.raises(ValueError):
        validate_inputs(data)


def test_validate_inputs_raises_on_ticker_mismatch():
    """A ticker present in PortfolioWeights but missing from
    SecurityMaster should be caught, not silently ignored."""
    data = {
        "SecurityMaster": pd.DataFrame(
            {
                "Ticker": ["A", "B"],
                "Asset Type": ["Equity", "Bond"],
                "Sector": ["Tech", "Financials"],
                "Country": ["United States", "United States"],
                "Rating": ["NR", "AA"],
                "Currency": ["USD", "USD"],
            }
        ),
        "PortfolioWeights": pd.DataFrame(
            {
                "Ticker": ["A", "C"],  # 'C' doesn't exist in SecurityMaster
                "Weight": [0.5, 0.5],
            }
        ),
        "TotalReturnIndex_Local": pd.DataFrame(
            {
                "Date": pd.to_datetime(["2024-01-01"]),
                "A": [100.0],
                "B": [100.0],
            }
        ),
    }

    with pytest.raises(ValueError):
        validate_inputs(data)


def test_validate_inputs_raises_on_unexplained_price_discrepancy():
    """A discrepancy between TRI and RawPrice on a date NOT listed in
    CorporateActions should be caught as an unexplained data quality
    issue, not silently accepted."""
    dates = pd.to_datetime(["2024-01-01", "2024-01-02"])
    data = {
        "SecurityMaster": pd.DataFrame(
            {
                "Ticker": ["A"],
                "Asset Type": ["Equity"],
                "Sector": ["Tech"],
                "Country": ["United States"],
                "Rating": ["NR"],
                "Currency": ["USD"],
            }
        ),
        "PortfolioWeights": pd.DataFrame({"Ticker": ["A"], "Weight": [1.0]}),
        "TotalReturnIndex_Local": pd.DataFrame({"Date": dates, "A": [100.0, 110.0]}),
        "RawPrice_Local": pd.DataFrame({"Date": dates, "A": [100.0, 50.0]}),  # unexplained jump
        "CorporateActions": pd.DataFrame({"Ticker": [], "Effective Date": []}),  # no known splits
    }

    with pytest.raises(ValueError):
        validate_inputs(data)


def test_summarize_missing_data_finds_known_missing_value():
    """A single injected NaN should be found and reported with the
    correct ticker and date."""
    tri = pd.DataFrame(
        {
            "Date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "AAA": [100.0, None],
            "BBB": [50.0, 51.0],
        }
    )

    result = summarize_missing_data(tri)

    assert len(result) == 1
    assert result.iloc[0]["Ticker"] == "AAA"
    assert result.iloc[0]["Date"] == pd.Timestamp("2024-01-02")
