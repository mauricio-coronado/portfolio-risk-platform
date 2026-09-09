# Sagard Risk Platform

A compact portfolio risk product turning raw portfolio and market data into performance, risk, exposure, and stress-scenario views for a portfolio manager.

**Universe:** 300 securities (120 Equities, 120 Bonds, 60 Loans), USD base currency, daily data from 2024-01-02 to 2025-12-31.

See [`methodology.md`](./methodology.md) for full assumptions, limitations, testing summary, and a required-conventions-to-code mapping.

## Project structure

```
.
├── data/
│   └── candidate_data.xlsx
├── src/
│   ├── data_loader.py      # Load, validate, FX conversion, missing-data reporting
│   ├── returns.py          # Security/portfolio return calculations
│   ├── risk_metrics.py     # Cumulative return, volatility, VaR, ES, drawdown
│   ├── exposure.py         # Net/gross/short reconciliation, breakdowns by dimension
│   ├── stress.py           # Equity/rate shock scenarios, sensitivity surface
│   └── dashboard.py        # KPI cards and the single-page dashboard figure
├── tests/                  # pytest suite, 22 tests across the five modules above
├── main.py                 # Runs the full pipeline end to end, prints results
├── dashboard.ipynb         # Interactive dashboard (date range, exposure dimension)
├── README.md               # This file
├── methodology.md          # One-page methodology note + conventions appendix
└── requirements.txt
```

## Running locally

```bash
# Create and activate a virtual environment (Python 3.11 recommended)
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Run the full pipeline (prints validation, KPIs, exposure, stress results)
python main.py
```

## Running the dashboard

```bash
jupyter notebook dashboard.ipynb
```

Run both cells. The dashboard renders with a start/end date picker and an exposure-dimension dropdown (Asset Type, Sector, Country, Rating); both update the chart immediately. Stress results are point-in-time (based on current security data) and don't change with either control.

## Running tests

```bash
python -m pytest tests/ -v
```

22 tests covering known-answer calculations (e.g. drawdown on a hand-computed wealth path, VaR/ES on a distribution with a calculable percentile), edge cases (day-one NaN, low-coverage exclusion), and validation/reconciliation logic.

## Key design choices

- **TotalReturnIndex_Local**, not RawPrice_Local, is used for all returns; RawPrice_Local contains unadjusted corporate-action jumps (verified against all three documented splits).
- **No forward-fill.** Missing values (3 of 156,600 possible observations) are excluded per-security; portfolio-level coverage is tracked daily, with a two-tier warn/exclude threshold.
- **Constant daily rebalancing**, per the workbook's README: portfolio and group returns represent a hypothetical backtest of today's weights, not a historical performance record.
- **Stress results** are shown as a continuous sensitivity surface (equity shock × rate shock), with the three required scenarios marked as specific points on it, rather than three isolated bars.

Full reasoning and evidence for each of these lives in `methodology.md`.