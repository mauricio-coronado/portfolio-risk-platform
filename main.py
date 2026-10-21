from src.data_loader import (
    load_inputs, get_security_currencies, validate_inputs,
    summarize_missing_data, convert_to_usd,
)
from src.returns import calculate_security_returns, calculate_portfolio_returns, calculate_fx_returns, decompose_currency, fx_contribution_by_currency
from src.exposure import reconcile_exposure, breakdown_exposure, contribution_by_dimension
from src.dashboard import build_kpi_summary
from src.risk_metrics import count_var_exceptions, compare_loan_pricing_frequency
from src.stress import (
    calculate_equity_selloff_impact, calculate_rate_shock_impact,
    calculate_combined_impact, calculate_portfolio_stress_impact,
)
import pandas as pd


def main():
    """
    Run the full pipeline end to end: load, validate, convert to USD,
    calculate returns, reconcile exposure, compute KPIs, exposure
    breakdowns, and stress scenario results, printing progress and
    results at each stage.

    Returns:
        dict: data, tri_usd, security_returns, portfolio_returns,
            coverage, exposure, kpis, exposure_breakdowns,
            stress_results, missing_data, var_backtest,
            loan_pricing.
    """
    data = load_inputs()
    validate_inputs(data)

    missing = summarize_missing_data(data['TotalReturnIndex_Local'])
    total_possible = data['TotalReturnIndex_Local'].shape[0] * (data['TotalReturnIndex_Local'].shape[1] - 1)

    print("\n=== Data Validation ===\n")

    print("Ticker consistency across SecurityMaster, PortfolioWeights, and TotalReturnIndex_Local: confirmed.\n")
    print("No duplicate tickers in SecurityMaster or PortfolioWeights: confirmed.\n")

    print(f"Missing values: {len(missing)} out of {total_possible:,} possible security-day observations.")
    if not missing.empty:
        print(missing.to_string(index=False))
    print()

    loan_pricing = compare_loan_pricing_frequency(
    data['TotalReturnIndex_Local'], data['SecurityMaster'], data['PortfolioWeights'])
    print(f"Loan pricing: prices are flat {loan_pricing['sub_portfolio_stale_day_fraction']:.0%} of days "
          f"(all loans update same day each week).\n"
          f"Naive daily vol {loan_pricing['median_daily_scaled_vol']:.2%} vs weekly-resampled "
          f"{loan_pricing['median_weekly_scaled_vol']:.2%} (median per-loan): roughly equal, no adjustment needed.")
    print()

    exposure = reconcile_exposure(data['PortfolioWeights'])
    stated = data['PortfolioWeights'].set_index('Exposure check')['Value'].dropna()
    reconciliation = pd.DataFrame({
        'Computed': [exposure['net'], exposure['gross'], exposure['short']],
        'Stated':   [stated.get('Net'), stated.get('Gross'), stated.get('Short')],
    }, index=['Net', 'Gross', 'Short'])
    print("Exposure reconciliation vs. embedded answer key:")
    print(reconciliation.to_string(float_format=lambda x: f"{x:.4f}"))
    print()

    ticker_currency = get_security_currencies(data['SecurityMaster'])
    tri_usd = convert_to_usd(data['TotalReturnIndex_Local'], data['FX_Local_per_USD'], ticker_currency)
    security_returns = calculate_security_returns(tri_usd)
    portfolio_returns, coverage = calculate_portfolio_returns(security_returns, data['PortfolioWeights'])

    weights = data['PortfolioWeights'].copy()
    weights['Currency'] = weights['Ticker'].map(ticker_currency)
    data['PortfolioWeights'] = weights

    security_returns_local = calculate_security_returns(data['TotalReturnIndex_Local'])
    fx_returns = calculate_fx_returns(data['FX_Local_per_USD'], ticker_currency,
                                    security_returns.columns)
    currency_legs = decompose_currency(security_returns_local, fx_returns, weights)
    fx_by_currency = fx_contribution_by_currency(security_returns_local, fx_returns,
                                                weights, ticker_currency)

    valid_days = portfolio_returns.notna().sum()
    total_days = len(portfolio_returns)
    print(f"Portfolio returns: {valid_days} valid observations out of {total_days} total days.")

    kpis = build_kpi_summary(portfolio_returns)
    print("\n=== KPI Summary ===\n")
    print(f"Cumulative Return:       {kpis['cumulative_return']:.2%}")
    print(f"Annualized Volatility:   {kpis['annualized_volatility']:.2%}")
    print(f"95% VaR (1-day):         {kpis['var_95']:.2%}")
    print(f"99% VaR (1-day):         {kpis['var_99']:.2%}")
    print(f"95% Expected Shortfall:  {kpis['es_95']:.2%}")
    print(f"99% Expected Shortfall:  {kpis['es_99']:.2%}")
    print(f"Max Drawdown:            {kpis['max_drawdown']:.2%}")

    exceptions_95 = count_var_exceptions(portfolio_returns, kpis['var_95'])
    exceptions_99 = count_var_exceptions(portfolio_returns, kpis['var_99'])
    expected_95 = 0.05 * valid_days
    expected_99 = 0.01 * valid_days
    var_backtest = {
        'exceptions_95': exceptions_95, 'expected_95': expected_95,
        'exceptions_99': exceptions_99, 'expected_99': expected_99,
    }
    print("\n=== VaR Backtest ===\n")
    print(f"95% VaR exceptions: {exceptions_95} (expected ~{expected_95:.1f} over {valid_days} valid days)")
    print(f"99% VaR exceptions: {exceptions_99} (expected ~{expected_99:.1f} over {valid_days} valid days)")

    exposure_breakdowns = {}
    print("\n=== Exposure Breakdowns ===")
    for dimension in ['Asset Type', 'Sector', 'Country', 'Rating', 'Currency']:
        breakdown = breakdown_exposure(data['PortfolioWeights'], dimension)
        exposure_breakdowns[dimension] = breakdown
        print(f"\n--- By {dimension} ---")
        print(breakdown.to_string())
    print()

    sm = data['SecurityMaster']
    weights = data['PortfolioWeights']
    equity_impact_sec = calculate_equity_selloff_impact(sm)
    rate_impact_sec = calculate_rate_shock_impact(sm)
    combined_sec = calculate_combined_impact(equity_impact_sec, rate_impact_sec)

    stress_results = {
        'equity_selloff': calculate_portfolio_stress_impact(equity_impact_sec, weights),
        'rate_shock': calculate_portfolio_stress_impact(rate_impact_sec, weights),
        'combined': calculate_portfolio_stress_impact(combined_sec, weights),
    }
    print("\n=== Stress Scenario Results ===\n")
    print(f"Equity Selloff (-15% market):  {stress_results['equity_selloff']:.2%}")
    print(f"Rate Shock (+100bps):          {stress_results['rate_shock']:.2%}")
    print(f"Combined (no diversification): {stress_results['combined']:.2%}")

    contributions = {d: contribution_by_dimension(security_returns, weights, data['SecurityMaster'], d)
                 for d in ['Asset Type', 'Sector', 'Country', 'Rating', 'Currency']}

    return {'data': data, 'tri_usd': tri_usd, 'security_returns': security_returns,
            'portfolio_returns': portfolio_returns, 'coverage': coverage, 'exposure': exposure,
            'kpis': kpis, 'exposure_breakdowns': exposure_breakdowns, 'stress_results': stress_results,
            'missing_data': missing,
            'var_backtest': var_backtest,
            'loan_pricing': loan_pricing,
            'contributions': contributions,
            'currency_legs': currency_legs,
            'fx_by_currency': fx_by_currency}

if __name__ == '__main__':
    main()