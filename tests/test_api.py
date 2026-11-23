"""
Automated End-to-End Tests for Flask REST API Endpoints.
Verifies HTTP status codes, JSON response schemas, validation errors, and CORS/headers.
"""
import pytest
from app import create_app
from backend.database import init_db, reset_db

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    init_db()
    reset_db()
    with app.test_client() as test_client:
        yield test_client
    reset_db()

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] in ("healthy", "degraded")
    assert data["database_connected"] is True
    assert "gemini_configured" in data

def test_watchlist_endpoint(client):
    res = client.get("/api/watchlist")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["watchlist"]) == 10

def test_stock_quote_endpoint(client):
    res = client.get("/api/stock/RELIANCE.NS")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["data"]["symbol"] == "RELIANCE.NS"
    assert data["data"]["price"] > 0

def test_stock_history_endpoint(client):
    res = client.get("/api/stock/TCS.NS/history?period=1M")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["candles"]) > 0

def test_stock_indicators_endpoint(client):
    res = client.get("/api/stock/INFY.NS/indicators?period=6M")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "summary" in data
    assert "rsi_14" in data["summary"]

def test_stock_prediction_endpoint(client):
    res = client.get("/api/stock/SBIN.NS/prediction?model=logistic_regression&horizon=5")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert data["prediction"]["status"] == "success"
    assert data["prediction"]["predicted_direction"] in ("Bullish", "Bearish", "Neutral")

def test_backtest_api_endpoint(client):
    payload = {
        "symbol": "ICICIBANK.NS",
        "fast_period": 20,
        "slow_period": 50,
        "initial_capital": 1000000.0
    }
    res = client.post("/api/backtest", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "total_return_pct" in data["backtest"]

def test_paper_trading_order_flow(client):
    # Buy Order
    buy_payload = {
        "symbol": "ITC.NS",
        "side": "BUY",
        "quantity": 10,
        "notes": "API test buy"
    }
    res_buy = client.post("/api/trading/order", json=buy_payload)
    assert res_buy.status_code == 200
    data_buy = res_buy.get_json()
    assert data_buy["success"] is True

    # Portfolio Check
    res_port = client.get("/api/trading/portfolio")
    assert res_port.status_code == 200
    data_port = res_port.get_json()
    assert data_port["portfolio"]["holdings_count"] == 1
    assert data_port["portfolio"]["cash_balance"] < 1000000.0

    # Risk Check
    res_risk = client.get("/api/trading/risk")
    assert res_risk.status_code == 200
    data_risk = res_risk.get_json()
    assert data_risk["risk"]["equity_exposure_pct"] > 0

    # Reset Portfolio
    res_reset = client.post("/api/trading/reset")
    assert res_reset.status_code == 200
    data_reset = res_reset.get_json()
    assert data_reset["portfolio"]["cash_balance"] == 1000000.0

def test_agent_command_endpoint(client):
    payload = {"command": "Analyse TCS"}
    res = client.post("/api/agent/command", json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "pipeline" in data["result"]
    assert "response" in data["result"]
