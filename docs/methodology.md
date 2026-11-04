# Methodology Note

## Scope

This platform validates portfolio and market data, calculates daily USD returns, performance and risk metrics (VaR, ES, drawdown), exposure breakdowns, and stress scenario results for a 300-security multi-asset portfolio (120 Equities, 120 Bonds, 60 Loans), presented in an interactive single-page dashboard.

The input workbook is synthetic. It reproduces a set of data-quality conditions on purpose, which is what the validation layer exists to catch; see the Data section of the README. Every figure quoted below is a property of that file, not a claim about any real portfolio.

## Key methodology decisions

The conventions this platform commits to (total return index rather than raw price, FX direction, signed weights, drawdown from compounded wealth, the VaR/ES quantile rule, the stress formulas) are listed in the Appendix alongside where each is implemented. This section covers the judgment calls behind them.

**Returns.** TotalReturnIndex_Local is used, not RawPrice_Local: RawPrice_Local shows artificial jumps at all three documented corporate-action dates, which would corrupt returns and risk metrics if used.

**Missing data.** Not forward-filled. Only 3 values are missing across 156,600 possible security-day observations, 6 lost daily returns after `pct_change` (see Assumptions). Portfolio-level coverage is tracked daily; below 99% is flagged, below 95% the day's return is excluded; only day one triggers exclusion in practice. Final: 521 of 522 valid days.

**Portfolio construction.** Weights are a single static vector representing constant daily rebalancing, so returns are a hypothetical backtest ("if today's weights had been held, rebalanced daily"), not historical fund performance. They are also frictionless: transaction costs are not modelled.

**Exposure.** Net, gross, and short are computed independently and reconciled exactly against the stated net, gross and short figures carried in PortfolioWeights, before any risk calculation runs. If they disagree, the run stops. NR is kept as a legitimate rating category (all Equities are NR), not dropped. A divergence metric (gross − |net|) flags where net alone might misrepresent true exposure; for this portfolio, no bucket shows the dramatic offsetting pattern (largest divergence roughly 5%, NR rating).

**Risk metrics.** VaR/ES use the empirical historical distribution, linear interpolation (numpy default), chosen for being the standard, unbiased convention, and reported as positive loss percentages.

Historical VaR/ES use the full 521-day sample with equal weighting rather than age-weighting (BRW) or volatility-scaling (Hull-White). The sample contains one selloff episode, so volatility is not flat year to year (6.35% in 2024 against 7.22% in 2025), but the worst 20 daily losses still fall across all eight quarters, 1 to 6 per quarter with gaps of 1 to 83 days. There is no sustained regime shift that recency-weighting would capture, and down-weighting the older half would discard the episode that matters most for the tail.

Maximum drawdown is computed from compounded wealth, not a cumulative sum of returns, since returns compound rather than add; the two methods only coincide when the trough immediately follows the peak.

**Stress testing.** Equity Selloff and Rate Shock use SecurityMaster's supplied sensitivities directly. Combined sums per-security impacts with no diversification offset, which is the conservative reading rather than the precise one. Beta and duration/convexity are local (first and second order) sensitivities; applying them at -15% and +100bp assumes they hold at that magnitude, a standard simplification rather than an exact repricing. Spread Duration, populated for all 180 Bond and Loan positions, is unused: the rate shock is a risk-free curve move, priced via Effective Duration and Convexity, not the credit-spread move Spread Duration would capture. The combined impact of -8.65% is roughly 7x the 1-day 99% Expected Shortfall of -1.22%, and roughly 6x the worst single day in the sample.

## Assumptions

- A missing security's return, or an excluded day's portfolio return, is treated as 0% rather than reweighted around. Immaterial here (521 of 522 valid days, only day one excluded), but a deliberate simplification, not an oversight.
- Volatility is annualized with the standard 252-day convention; the file has roughly 260 observations per year but 252 is kept so the figure stays comparable to any externally reported "annualized" number.
- The 99% and 95% coverage thresholds that flag or exclude low-coverage days are illustrative, not calibrated values; a production deployment would tune them against observed coverage patterns and loss tolerance.
- Equity Beta and Duration/Convexity are used as supplied, with no adjustment for the currency basis they were presumably estimated in (a non-USD security's beta is typically estimated against its own local market).

## Limitations

- Portfolio and group cumulative returns are a rebalanced-portfolio backtest, not a record of actual historical portfolio composition, which the dataset does not carry.
- TotalReturnIndex_Local is intended to include income adjustment, but no measurable income effect is present: it differs from RawPrice_Local only on the three corporate-action dates, so income accrual is not separately modelled in this dataset.
- Loan securities are priced weekly, which was investigated as a possible source of understated volatility. Volatility measured from daily prices (4.30%) is nearly identical to volatility measured from weekly prices (4.35%), so no adjustment was needed at the portfolio level. Loan prices do not move on 80% of days, because all loans update on the same day each week. Staleness could in principle distort portfolio-level VaR/ES: on non-repricing days loans show no interaction with equity or bond moves, and on repricing days a full week's return lands in a single day, either of which could shift which days rank in the tail. Loans are a smaller, lower-volatility slice of the portfolio than equities and bonds, which should limit this effect, but it remains a theoretical risk worth flagging, particularly for a portfolio with a larger or more volatile loan allocation.
- Exposure is broken down by currency in the pipeline, but currency is not one of the dimensions offered in the dashboard dropdown, so the currency view is available in the printed output and not interactively.
- Exposure is reconciled against an independently stated figure. The risk metrics are pinned by tests, which stops them drifting, but nothing checks them against a second implementation.

## Testing

22 unit tests across `data_loader`, `returns`, `risk_metrics`, `kpis`, `exposure` and `stress`: known-answer checks, edge-case behaviour (day-one NaN, low-coverage exclusion, ticker mismatches raising explicit errors), and reconciliation against the stated exposure figures. One of the 22 runs the pipeline end to end and pins every headline figure, so a change in any module that moves a published number fails immediately rather than surfacing as a different answer on the dashboard.

VaR is also backtested in-sample: 27 breaches of the 95% threshold and 6 of the 99% threshold over the 521 valid days, against a theoretical 26 and 5, indicating good calibration.

## Production scaling

The calculation core is deliberately independent of how it is fed and where it runs: `pipeline.main()` takes a workbook and produces numbers, with no storage, scheduling or presentation logic inside it. That is what makes the remaining work additive rather than a rewrite.

The target shape is source ingestion into a staged layer on S3, with the structural checks in `validate_inputs` gating promotion to production tables rather than running after the fact; results persisted per run so that "why is this different from last Tuesday" is answerable; the pipeline running unattended on a schedule rather than cell by cell in a notebook; a hosted dashboard reading stored results through an API; and coverage-threshold breaches raising alerts instead of publishing quietly.

The README roadmap tracks the order these are being built in, and the architecture decisions behind them are recorded under `docs/adr/`.

# Appendix: Conventions Mapped to Code

| Convention | Where it is implemented |
|---|---|
| Use TotalReturnIndex_Local, not RawPrice_Local, and state why | `src/riskplatform/data_loader.py::convert_to_usd()` uses TotalReturnIndex_Local exclusively. |
| Convert to USD via FX_Local_per_USD (local units per USD 1) | `src/riskplatform/data_loader.py::convert_to_usd()` |
| Do not silently forward-fill; state final observation count and missing-data policy | `src/riskplatform/data_loader.py::summarize_missing_data()` reports the footprint before any policy is applied; `src/riskplatform/returns.py::calculate_security_returns()` uses `pct_change(fill_method=None)`; `src/riskplatform/returns.py::calculate_portfolio_returns()` implements the coverage-threshold exclusion policy. Final count stated above and printed by `pipeline.main()`. |
| Use signed weights; reconcile net, gross and short before calculating risk | `src/riskplatform/exposure.py::reconcile_exposure()`, called in `pipeline.main()` before any return or risk calculation, and checked against the figures stated in PortfolioWeights. |
| Compute max drawdown from compounded wealth, not a cumulative sum of returns | `src/riskplatform/risk_metrics.py::calculate_max_drawdown()` |
| Report VaR/ES as positive losses; state the empirical quantile rule | `src/riskplatform/risk_metrics.py::calculate_historical_var()` and `calculate_expected_shortfall()`; both use `numpy.percentile` default linear interpolation, stated in each docstring. |
| Break down signed net exposure by asset type, sector, country, rating and currency; show gross where it changes interpretation | `src/riskplatform/exposure.py::breakdown_exposure()`, including the `divergence` column (gross − \|net\|). |
| Apply a -15% equity shock and a +100bp rate shock, plus the combined case | `src/riskplatform/stress.py::calculate_equity_selloff_impact()`, `calculate_rate_shock_impact()`, `calculate_combined_impact()`; the combined case is verified to equal the exact sum of the two individual impacts. |
| Assemble headline metrics without a plotting dependency | `src/riskplatform/kpis.py::build_kpi_summary()`, so the calculation core can run in a container with no matplotlib. |
| Compact dashboard: performance, risk, exposure, stress, labelled units | `src/riskplatform/dashboard.py::build_dashboard_page()`; single-page 2x2 layout, all units labelled (%, bps) on every axis and card. |
