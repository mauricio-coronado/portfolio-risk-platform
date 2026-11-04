# Portfolio Risk Platform

A compact portfolio risk product turning raw portfolio and market data into performance, risk, exposure, and stress-scenario views for a portfolio manager.

See [`docs/methodology.md`](./docs/methodology.md) for full assumptions, limitations, testing summary, and a required-conventions-to-code mapping.

## Data

`data/portfolio.xlsx` is synthetic: 300 securities (120 equities, 120 bonds, 60 loans), six currencies with USD as the base, daily data from 2024-01-02 to 2025-12-31.

It reproduces on purpose the conditions the validation layer catches:

- Country and currency are correlated but not identical, so a country breakdown is a misleading proxy for currency exposure.
- Loans are marked weekly, so prices are flat on roughly four days in five.
- Three stock splits are adjusted in the total return index and not in the raw price; the corporate actions sheet is the only way to tell an adjustment from corrupt data.
- Three observations are missing, and are not filled in anywhere.
- One equity selloff, so the drawdown and VaR backtest describe a real episode.

**Limitation.** Generated data, not a market feed. Figures are properties of this file, not claims about a real portfolio. A live price and FX source is future work.

## Project structure

```
.
├── data/
│   └── portfolio.xlsx
├── docs/
│   └── methodology.md      # One-page methodology note + conventions appendix
├── src/riskplatform/
│   ├── data_loader.py      # Load, validate, FX conversion, missing-data reporting
│   ├── returns.py          # Security/portfolio return calculations
│   ├── risk_metrics.py     # Cumulative return, volatility, VaR, ES, drawdown
│   ├── exposure.py         # Net/gross/short reconciliation, breakdowns by dimension
│   ├── stress.py           # Equity/rate shock scenarios, sensitivity surface
│   ├── kpis.py             # Headline metric assembly, no plotting dependency
│   ├── dashboard.py        # KPI cards and the single-page dashboard figure
│   └── pipeline.py         # Runs the full pipeline end to end, prints results
├── tests/                  # pytest suite, 22 tests
├── dashboard.ipynb         # Interactive dashboard (date range, exposure dimension)
├── pyproject.toml          # Package metadata, dependencies, tool configuration
└── README.md               # This file
```

## Running locally

```bash
# Create and activate a virtual environment (Python 3.11 or later)
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# Install the package and its development and plotting extras
pip install -e ".[dev,viz]"

# Run the full pipeline (prints validation, KPIs, exposure, stress results)
riskplatform
```

## Running the dashboard

```bash
jupyter notebook dashboard.ipynb
```

Run both cells. The dashboard renders with a start/end date picker and an exposure-dimension dropdown (Asset Type, Sector, Country, Rating); both update the chart immediately. Stress results are point-in-time (based on current security data) and don't change with either control.

## Running tests

```bash
pytest
```

22 tests covering known-answer calculations (e.g. drawdown on a hand-computed wealth path, VaR/ES on a distribution with a calculable percentile), edge cases (day-one NaN, low-coverage exclusion), and validation/reconciliation logic.

## Key design choices

- **TotalReturnIndex_Local**, not RawPrice_Local, is used for all returns; RawPrice_Local contains unadjusted corporate-action jumps (verified against all three documented splits).
- **No forward-fill.** Missing values (3 of 156,600 possible observations) are excluded per-security; portfolio-level coverage is tracked daily, with a two-tier warn/exclude threshold.
- **Constant daily rebalancing.** Weights are a single static vector, so portfolio and group returns are a hypothetical backtest of today's weights rather than a historical performance record.
- **Stress results** are shown as a continuous sensitivity surface (equity shock × rate shock), with the three required scenarios marked as specific points on it, rather than three isolated bars.

Full reasoning and evidence for each of these lives in `docs/methodology.md`.