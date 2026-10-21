import pytest

from riskplatform.pipeline import main


def test_pipeline_output():
    """Runs the complete pipeline against the real 300-security workbook
    and checks its headline outputs against the values captured when this
    pipeline was reviewed. The other 19 tests exercise individual
    functions on small, synthetic inputs; this is the only one that runs
    the real end-to-end pipeline. If a future change to any module shifts
    one of these numbers, this fails immediately instead of the dashboard
    silently showing a different answer than the one reviewed and signed
    off on."""
    results = main()
    kpis = results["kpis"]

    assert kpis["cumulative_return"] == pytest.approx(-0.015537, abs=1e-5)
    assert kpis["annualized_volatility"] == pytest.approx(0.088880, abs=1e-5)
    assert kpis["var_95"] == pytest.approx(0.009613, abs=1e-5)
    assert kpis["var_99"] == pytest.approx(0.012507, abs=1e-5)
    assert kpis["es_95"] == pytest.approx(0.011932, abs=1e-5)
    assert kpis["es_99"] == pytest.approx(0.016119, abs=1e-5)
    assert kpis["max_drawdown"] == pytest.approx(-0.201981, abs=1e-5)
    assert kpis["valid_days"] == 521
    assert kpis["total_days"] == 522

    exposure = results["exposure"]
    assert exposure["net"] == pytest.approx(1.00, abs=1e-6)
    assert exposure["gross"] == pytest.approx(1.10, abs=1e-6)
    assert exposure["short"] == pytest.approx(-0.05, abs=1e-6)

    stress = results["stress_results"]
    assert stress["equity_selloff"] == pytest.approx(-0.0627, abs=1e-4)
    assert stress["rate_shock"] == pytest.approx(-0.0222, abs=1e-4)
    assert stress["combined"] == pytest.approx(-0.0850, abs=1e-4)
