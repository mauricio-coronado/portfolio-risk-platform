import pytest

from riskplatform.pipeline import main


def test_pipeline_output():
    """Runs the complete pipeline against the synthetic 300-security
    workbook and checks its headline outputs against the values captured
    when this pipeline was reviewed. The other 21 tests exercise individual
    functions on small inputs defined inline; this is the only one that runs
    the pipeline end to end. If a future change to any module shifts one of
    these numbers, this fails immediately instead of the dashboard silently
    showing a different answer than the one that was reviewed."""

    results = main()
    kpis = results["kpis"]

    assert kpis['cumulative_return'] == pytest.approx(-0.025986, abs=1e-5)
    assert kpis['annualized_volatility'] == pytest.approx( 0.068004, abs=1e-5)
    assert kpis['var_95'] == pytest.approx( 0.007110, abs=1e-5)
    assert kpis['var_99'] == pytest.approx( 0.009865, abs=1e-5)
    assert kpis['es_95'] == pytest.approx( 0.008982, abs=1e-5)
    assert kpis['es_99'] == pytest.approx( 0.012184, abs=1e-5)
    assert kpis['max_drawdown'] == pytest.approx(-0.115582, abs=1e-5)
    assert kpis['valid_days'] == 521
    assert kpis['total_days'] == 522

    exposure = results["exposure"]
    assert exposure["net"] == pytest.approx(1.00, abs=1e-6)
    assert exposure["gross"] == pytest.approx(1.10, abs=1e-6)
    assert exposure["short"] == pytest.approx(-0.05, abs=1e-6)

    stress = results['stress_results']
    assert stress['equity_selloff'] == pytest.approx(-0.0606, abs=1e-4)
    assert stress['rate_shock']     == pytest.approx(-0.0258, abs=1e-4)
    assert stress['combined']       == pytest.approx(-0.0865, abs=1e-4)
