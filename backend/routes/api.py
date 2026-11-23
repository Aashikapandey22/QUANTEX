"""
REST API Blueprint for QUANTEX Institutional Trading Terminal.
Provides comprehensive endpoints for market data, indicators, ML forecasting,
AI Agent execution, virtual paper trading, backtesting, and portfolio risk.
"""
from datetime import datetime, timezone
import pandas as pd
from flask import Blueprint, request, jsonify

from config import Config
from backend.database import get_db_connection, reset_db
from backend.market_data.symbols import normalize_symbol, get_symbol_meta
from backend.market_data.yahoo_provider import market_data_provider
from backend.analytics.indicators import calculate_technical_indicators, get_latest_indicators_summary
from backend.ml.pipeline import train_and_predict
from backend.trading.backtest import run_ma_crossover_backtest
from backend.trading.paper_trading import paper_trading_engine
from backend.analytics.risk import calculate_portfolio_risk
from backend.agents.gemini_analyst import gemini_analyst
from backend.agents.tool_agent import quantex_agent

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/health", methods=["GET"])
def health_check():
    """System health check and provider status."""
    db_ok = False
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database_connected": db_ok,
        "gemini_configured": gemini_analyst.is_configured(),
        "gemini_model": gemini_analyst.model_name,
        "configured_model": Config.GEMINI_MODEL,
        "active_engine": gemini_analyst.model_name if gemini_analyst.is_configured() else "QUANTEX Institutional Rule Engine v2.0",
        "virtual_trading_mode": "ACTIVE (Strict Virtual Money Only)"
    })

@api_bp.route("/watchlist", methods=["GET"])
def get_watchlist():
    """Returns quotes overview for default Indian equity watchlist."""
    try:
        quotes = market_data_provider.get_watchlist_overview()
        return jsonify({"success": True, "count": len(quotes), "watchlist": quotes})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@api_bp.route("/stock/<symbol>", methods=["GET"])
def get_stock_quote(symbol):
    """Returns quote snapshot and corporate metadata for a single symbol."""
    norm = normalize_symbol(symbol)
    quote = market_data_provider.get_quote(norm)
    return jsonify({"success": True, "data": quote})

@api_bp.route("/stock/<symbol>/history", methods=["GET"])
def get_stock_history(symbol):
    """Returns historical daily OHLCV candlestick data."""
    norm = normalize_symbol(symbol)
    period = request.args.get("period", "1Y").upper()
    if period not in ("1M", "3M", "6M", "1Y", "2Y"):
        period = "1Y"

    df, status_meta = market_data_provider.get_historical_data(norm, period=period)
    
    # Format for charting libraries (Candlestick + Volume)
    records = []
    for idx, row in df.iterrows():
        date_str = idx.strftime("%Y-%m-%d") if isinstance(idx, datetime) else str(idx)
        records.append({
            "date": date_str,
            "open": float(row["Open"]),
            "high": float(row["High"]),
            "low": float(row["Low"]),
            "close": float(row["Close"]),
            "volume": int(row["Volume"])
        })

    return jsonify({
        "success": True,
        "symbol": norm,
        "period": period,
        "count": len(records),
        "status_meta": status_meta,
        "candles": records
    })

@api_bp.route("/stock/<symbol>/indicators", methods=["GET"])
def get_stock_indicators(symbol):
    """Returns calculated technical indicators on historical data."""
    norm = normalize_symbol(symbol)
    period = request.args.get("period", "6M").upper()
    df, status_meta = market_data_provider.get_historical_data(norm, period=period)
    df_ind = calculate_technical_indicators(df)
    summary = get_latest_indicators_summary(df_ind)

    # Return series for overlays (SMA 20, SMA 50, EMA 20, RSI, MACD)
    series_data = []
    for idx, row in df_ind.tail(60).iterrows():
        date_str = idx.strftime("%Y-%m-%d") if isinstance(idx, datetime) else str(idx)
        series_data.append({
            "date": date_str,
            "close": float(row["Close"]),
            "sma_20": float(row["SMA_20"]) if pd.notnull(row["SMA_20"]) else None,
            "sma_50": float(row["SMA_50"]) if pd.notnull(row["SMA_50"]) else None,
            "ema_20": float(row["EMA_20"]) if pd.notnull(row["EMA_20"]) else None,
            "rsi_14": float(row["RSI_14"]) if pd.notnull(row["RSI_14"]) else None,
            "macd": float(row["MACD"]) if pd.notnull(row["MACD"]) else None,
            "macd_signal": float(row["MACD_Signal"]) if pd.notnull(row["MACD_Signal"]) else None,
            "macd_hist": float(row["MACD_Hist"]) if pd.notnull(row["MACD_Hist"]) else None
        })

    return jsonify({
        "success": True,
        "symbol": norm,
        "summary": summary,
        "series": series_data,
        "status_meta": status_meta
    })

@api_bp.route("/stock/<symbol>/prediction", methods=["GET"])
def get_stock_prediction(symbol):
    """Generates directional ML prediction over horizon (default: 5 days)."""
    norm = normalize_symbol(symbol)
    model_type = request.args.get("model", "logistic_regression")
    horizon = int(request.args.get("horizon", "5"))

    df, status_meta = market_data_provider.get_historical_data(norm, period="1Y")
    result = train_and_predict(df, model_type=model_type, horizon=horizon)
    result["symbol"] = norm
    result["market_status"] = status_meta

    return jsonify({"success": True, "prediction": result})

@api_bp.route("/analyst/explain", methods=["POST"])
def explain_stock_analyst():
    """Generates institutional briefing using Gemini or local quant engine."""
    data = request.get_json() or {}
    symbol = data.get("symbol", "RELIANCE.NS")
    norm = normalize_symbol(symbol)

    quote = market_data_provider.get_quote(norm)
    df, _ = market_data_provider.get_historical_data(norm, period="1Y")
    df_ind = calculate_technical_indicators(df)
    indicators = get_latest_indicators_summary(df_ind)
    ml_result = train_and_predict(df, model_type="logistic_regression", horizon=5)

    analysis = gemini_analyst.explain_stock(norm, quote, indicators, ml_result)
    return jsonify({
        "success": True,
        "symbol": norm,
        "analyst_response": analysis,
        "source": "gemini" if gemini_analyst.is_configured() else "local_quant_engine"
    })

@api_bp.route("/agent/command", methods=["POST"])
def agent_command():
    """Executes natural language command via PLAN -> ACT -> OBSERVE -> RESPOND loop."""
    data = request.get_json() or {}
    query = data.get("command", "").strip()

    if not query:
        return jsonify({"success": False, "error": "Command parameter is required."}), 400

    agent_result = quantex_agent.run(query)
    return jsonify({
        "success": True,
        "result": agent_result
    })

@api_bp.route("/backtest", methods=["POST"])
def backtest_strategy():
    """Executes Moving Average crossover backtest."""
    data = request.get_json() or {}
    symbol = normalize_symbol(data.get("symbol", "RELIANCE.NS"))
    fast_period = int(data.get("fast_period", 20))
    slow_period = int(data.get("slow_period", 50))
    initial_cap = float(data.get("initial_capital", Config.INITIAL_CAPITAL))

    df, status_meta = market_data_provider.get_historical_data(symbol, period="1Y")
    bt_res = run_ma_crossover_backtest(df, fast_period=fast_period, slow_period=slow_period, initial_capital=initial_cap)
    bt_res["symbol"] = symbol
    bt_res["status_meta"] = status_meta

    return jsonify({"success": True, "backtest": bt_res})

@api_bp.route("/trading/portfolio", methods=["GET"])
def get_portfolio():
    """Returns virtual paper trading portfolio balance, holdings, and P&L."""
    port = paper_trading_engine.get_portfolio()
    return jsonify({"success": True, "portfolio": port})

@api_bp.route("/trading/order", methods=["POST"])
def place_order():
    """Places a virtual BUY or SELL paper trade."""
    data = request.get_json() or {}
    symbol = data.get("symbol")
    side = data.get("side")
    quantity = data.get("quantity")
    notes = data.get("notes", "")

    if not symbol or not side or not quantity:
        return jsonify({"success": False, "error": "Missing required fields: symbol, side, quantity."}), 400

    try:
        qty = int(quantity)
    except ValueError:
        return jsonify({"success": False, "error": "Quantity must be an integer."}), 400

    res = paper_trading_engine.execute_order(symbol=symbol, side=side, quantity=qty, notes=notes)
    if not res.get("success"):
        return jsonify({"success": False, "error": res.get("error")}), 400

    return jsonify({"success": True, "data": res})

@api_bp.route("/trading/transactions", methods=["GET"])
def get_transactions():
    """Returns virtual trade history."""
    limit = int(request.args.get("limit", 50))
    txns = paper_trading_engine.get_transactions(limit=limit)
    return jsonify({"success": True, "transactions": txns})

@api_bp.route("/trading/risk", methods=["GET"])
def get_risk_metrics():
    """Returns institutional risk analytics on active virtual portfolio."""
    risk = calculate_portfolio_risk()
    return jsonify({"success": True, "risk": risk})

@api_bp.route("/trading/reset", methods=["POST"])
def reset_portfolio():
    """Resets virtual paper trading account to default capital."""
    reset_db()
    port = paper_trading_engine.get_portfolio()
    return jsonify({"success": True, "message": "Virtual trading account successfully reset to ₹10,00,000.", "portfolio": port})
