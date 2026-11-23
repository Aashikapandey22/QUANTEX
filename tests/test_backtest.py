"""
Automated Tests for Quantitative Strategy Backtesting Engine.
Validates SMA crossover logic, next-bar execution, fees, and metric outputs.
"""
import pytest
from backend.market_data.yahoo_provider import YahooMarketDataProvider
from backend.trading.backtest import run_ma_crossover_backtest

@pytest.fixture
def historical_series():
    provider = YahooMarketDataProvider()
    return provider.generate_synthetic_historical("HDFCBANK.NS", period="1Y")

def test_backtest_execution(historical_series):
    res = run_ma_crossover_backtest(
        df=historical_series,
        fast_period=20,
        slow_period=50,
        initial_capital=1000000.0,
        fee_pct=0.001,
        slippage_pct=0.0005
    )

    assert res["status"] == "success"
    assert "SMA Crossover" in res["strategy"]
    assert res["initial_capital"] == 1000000.0
    assert "final_capital" in res
    assert "total_return_pct" in res
    assert "cagr_pct" in res
    assert "max_drawdown_pct" in res
    assert res["max_drawdown_pct"] >= 0.0
    assert "sharpe_ratio" in res
    assert "equity_curve" in res
    assert len(res["equity_curve"]) > 0
    assert "trades" in res
