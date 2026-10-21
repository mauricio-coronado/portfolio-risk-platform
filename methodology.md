# Methodology Note

## Scope

This platform validates portfolio and market data, calculates daily USD returns, performance and risk metrics (VaR, ES, drawdown), exposure breakdowns, and stress scenario results for a 300-security multi-asset portfolio (120 Equities, 120 Bonds, 60 Loans), presented in an interactive single-page dashboard.

## Key methodology decisions

Required conventions from the brief (TRI vs. RawPrice, FX direction, signed weights, drawdown from wealth, VaR/ES convention, stress formulas) are followed as specified; see the Appendix for exactly where each is implemented in code. This section covers the judgment calls beyond what the brief dictates.

**Returns.** TotalReturnIndex_Local is used, not RawPrice_Local: RawPrice_Local shows artificial jumps at all three documented corporate-action dates, which would corrupt returns and risk metrics if used.

**Missing data.** Not forward-filled. Only 3 values are missing across 156,600 possible security-day observations, 6 lost daily returns after `pct_change` (see Assumptions). Portfolio-level coverage is tracked daily; below 99% is flagged, below 95% the day's return is excluded; only day one triggers exclusion in practice. Final: 521 of 522 valid days.

**Portfolio construction.** Weights represent constant daily rebalancing per the workbook's README, so returns are a hypothetical backtest ("if today's weights had been held, rebalanced daily"), not historical fund performance, and are frictionless: transaction costs  are not modelled.

**Exposure.** Net, gross, and short reconciled exactly against the workbook's embedded answer key before any risk calculation. NR is kept as a legitimate rating category (all Equities are NR), not dropped.  A divergence metric (gross − |net|) flags where net alone might misrepresent true exposure; for this portfolio, no bucket shows the dramatic offsetting pattern (largest divergence ~6%, NR rating).


**Risk metrics.** VaR/ES use the empirical historical distribution, linear interpolation (numpy default), chosen for being the standard, unbiased convention, and reported as positive loss percentages. Historical VaR/ES use the full 521-day sample with equal weighting rather than age-weighting (BRW) or volatility-scaling (Hull-White): annualized volatility is stable year-over-year (8.99% vs. 8.66%) and the worst 20 daily losses are spread across all eight quarters (1-5 per quarter, gaps of 1-146 days), so there's no regime-shift or clustering signal that recency-weighting would meaningfully capture. Maximum drawdown is computed from compounded wealth, not a cumulative sum of returns, since returns compound rather than add; the two methods only coincide when the trough immediately follows the peak.

**Stress testing.** Equity Selloff and Rate Shock use SecurityMaster's supplied sensitivities directly. Combined sums per-security impacts with no diversification offset, per the sheet's explicit method. Beta and duration/convexity are local (first/second-order) sensitivities; applying them at -15%/+100bp assumes they hold at that magnitude, a standard simplification rather than an exact repricing. Spread Duration, populated for all 180 Bond/Loan positions, is unused: Rate shock is a risk-free curve move, priced via Effective Duration and Convexity, not the credit-spread move Spread Duration would capture. The combined impact of -8.50% is roughly 5x the 1-day 99% Expected Shortfall of -1.61%, equivalent in scale to several consecutive worst-case trading days.

## Assumptions

- A missing security's return, or an excluded day's portfolio return, is treated as 0% rather than reweighted around. Immaterial here (521/522 valid days, only day 1 missing), but a deliberate simplification, not an oversight.
- Volatility is annualized with the standard 252-day convention; the file has ~260 observations/year but 252 is kept so the figure stays comparable to any externally reported "annualized" number.
- The 99%/95% coverage thresholds that flag or exclude low-coverage days are illustrative choices for this exercise, not production-calibrated values; a real deployment would tune them against actual historical coverage patterns and loss tolerance.
- Equity Beta and Duration/Convexity are used as supplied, with no adjustment for the currency basis they were presumably estimated in (a non-USD security's beta is typically estimated against its own local market).

## Limitations

- TotalReturnIndex_Local is documented as including income adjustment; no measurable income effect was found empirically (differences from RawPrice_Local occur only on the three known corporate-action dates), suggesting income accrual isn't separately modelled in this dataset.
- Portfolio/group cumulative returns are a rebalanced-portfolio backtest, not a record of actual historical fund composition, which isn't provided in the dataset.

- Loan securities are priced weekly (confirmed via the README and empirically); investigated whether this understates volatility. Volatility measured from daily prices (1.72%) is nearly identical to volatility measured correctly from weekly prices (1.74%), so no adjustment was needed at the portfolio level. Loan prices don't move on 80% of days, because all loans update on the same day each week. Staleness could in principle distort portfolio-level VaR/ES: on non-repricing days loans show no interaction with equity or bond moves, and on repricing days a full week's return lands in a single day, either of which could shift which days rank in the tail. Loans are a smaller, lower-volatility slice of the portfolio than equities and bonds, which should limit this effect, but it remains a theoretical risk worth flagging, particularly for a portfolio with a larger or more volatile loan allocation.
-  No dedicated currency exposure view was built beyond the required Asset Type/Sector/Country/Rating breakdowns.

## Testing

22 unit tests across data_loader, returns, risk_metrics, exposure, and stress modules: known-answer checks, edge-case behaviour (day-one NaN, low-coverage exclusion, ticker mismatches raising explicit errors), and reconciliation against the workbook's embedded answer key. 

VaR is also backtested in-sample: 27 breaches of the 95% threshold and 6 of the 99% threshold over the 521 valid days, against a theoretical ~26 and ~5, indicating good calibration.

## Production-scaling approach

Source ingestion via APIs into a staged cloud data layer (e.g. GCS/BigQuery), with automated data-quality checks (structural validation, completeness, FX/sensitivity checks, mirroring validate_inputs here) gating promotion to production tables. Code lives in a version-controlled repo (git/GitHub); pipeline changes run through CI (pytest, as in this submission) on every pull request before merge. The notebook here would become an unattended scheduled job rather than something run cell-by-cell, with the dashboard becoming a hosted app (e.g. a scheduled Dash/Streamlit service or Power BI) reading from the production data layer, and coverage-threshold breaches triggering alerts rather than silent publication.
# Appendix: Required Conventions Mapped to Code

| Required convention | Where it's implemented |
|---|---|
| Use TotalReturnIndex_Local, not RawPrice_Local; explain why | `src/data_loader.py::convert_to_usd()` uses TotalReturnIndex_Local exclusively. |
| Convert to USD via FX_Local_per_USD (local units per USD 1) | `src/data_loader.py::convert_to_usd()` |
| Do not silently forward-fill; state final observation count and missing-data policy | `src/data_loader.py::summarize_missing_data()` reports the footprint before any policy is applied; `src/returns.py::calculate_security_returns()` uses `pct_change(fill_method=None)`; `src/returns.py::calculate_portfolio_returns()` implements the coverage-threshold exclusion policy. Final count stated above and printed by `main()`. |
| Use signed weights; reconcile net, gross, and short before calculating risk | `src/exposure.py::reconcile_exposure()`, called in `main()` before any return/risk calculation; verified against the workbook's embedded answer key. |
| Compute max drawdown from compounded wealth, not cumulative sum of returns | `src/risk_metrics.py::calculate_max_drawdown()`. |
| Report VaR/ES as positive losses; state the empirical quantile rule | `src/risk_metrics.py::calculate_historical_var()` / `calculate_expected_shortfall()`; both use `numpy.percentile` default linear interpolation, stated in each docstring. |
| Break down signed net exposure by asset type, sector, country, rating; show gross where it changes interpretation | `src/exposure.py::breakdown_exposure()`, including the `divergence` column (gross − \|net\|). |
| Run supplied -15% equity and +100bp rate shocks, plus combined | `src/stress.py::calculate_equity_selloff_impact()`, `calculate_rate_shock_impact()`, `calculate_combined_impact()`; combined verified to equal the exact sum of the two individual impacts. |
| Compact dashboard: performance, risk, exposure, stress, labelled units | `src/dashboard.py::build_dashboard_page()`; single-page 2x2 layout, all units labelled (%, bps) on every axis/card. |
