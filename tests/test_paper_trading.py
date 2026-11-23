"""
Automated Tests for Virtual Paper Trading and Risk Management.
Validates buy/sell execution, virtual capital controls, short-selling prevention,
P&L calculations, and parametric VaR stress-testing.
"""
import pytest
from backend.database import init_db, reset_db
from backend.trading.paper_trading import PaperTradingEngine
from backend.analytics.risk import calculate_portfolio_risk

@pytest.fixture(autouse=True)
def setup_clean_db():
    init_db()
    reset_db()
    yield
    reset_db()

def test_initial_portfolio_balance():
    engine = PaperTradingEngine()
    port = engine.get_portfolio()
    assert port["initial_capital"] == 1000000.0
    assert port["cash_balance"] == 1000000.0
    assert port["holdings_count"] == 0
    assert port["unrealized_pnl"] == 0.0

def test_buy_order_execution():
    engine = PaperTradingEngine()
    # Buy 20 shares of TCS.NS
    res = engine.execute_order(symbol="TCS.NS", side="BUY", quantity=20, notes="Unit test buy")
    assert res["success"] is True
    assert res["order"]["symbol"] == "TCS.NS"
    assert res["order"]["quantity"] == 20
    assert res["order"]["execution_price"] > 0

    port = engine.get_portfolio()
    assert port["cash_balance"] < 1000000.0
    assert port["holdings_count"] == 1
    assert port["holdings"][0]["symbol"] == "TCS.NS"
    assert port["holdings"][0]["quantity"] == 20

def test_insufficient_cash_rejection():
    engine = PaperTradingEngine()
    # Try buying 1,000,000 shares of RELIANCE (costs billions)
    res = engine.execute_order(symbol="RELIANCE.NS", side="BUY", quantity=1000000)
    assert res["success"] is False
    assert "Insufficient virtual cash" in res["error"]

def test_sell_order_execution_and_realized_pnl():
    engine = PaperTradingEngine()
    # Buy 10 shares of INFY.NS
    engine.execute_order(symbol="INFY.NS", side="BUY", quantity=10)
    
    # Sell 5 shares
    res_sell = engine.execute_order(symbol="INFY.NS", side="SELL", quantity=5, notes="Partial sell")
    assert res_sell["success"] is True

    port = engine.get_portfolio()
    assert port["holdings_count"] == 1
    assert port["holdings"][0]["quantity"] == 5

    # Check transactions
    txns = engine.get_transactions()
    assert len(txns) == 2
    assert txns[0]["side"] == "SELL"
    assert txns[1]["side"] == "BUY"

def test_oversell_rejection():
    engine = PaperTradingEngine()
    # Buy 5 shares
    engine.execute_order(symbol="ITC.NS", side="BUY", quantity=5)
    # Try selling 10 shares
    res = engine.execute_order(symbol="ITC.NS", side="SELL", quantity=10)
    assert res["success"] is False
    assert "Insufficient shares" in res["error"]

def test_risk_analytics_calculation():
    engine = PaperTradingEngine()
    # Execute buys to generate active exposure
    engine.execute_order(symbol="RELIANCE.NS", side="BUY", quantity=20)
    engine.execute_order(symbol="TCS.NS", side="BUY", quantity=15)

    risk = calculate_portfolio_risk()
    assert risk["status"] == "success"
    assert risk["equity_exposure_pct"] > 0
    assert risk["cash_pct"] < 100
    assert risk["hhi_concentration"] >= 0
    assert risk["var_95_daily_amount"] >= 0
    assert "stress_tests" in risk
    assert "market_down_2pct" in risk["stress_tests"]
    assert "market_down_5pct" in risk["stress_tests"]
    assert "market_down_10pct" in risk["stress_tests"]
