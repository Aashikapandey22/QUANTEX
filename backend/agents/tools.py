"""
Approved Tool Execution Registry for QUANTEX Autonomous AI Agent.
Provides validated, sandboxed entry points to backend quantitative engines.
STRICT SECURITY: Never executes arbitrary Python, eval, or shell commands.
"""
import logging
from backend.market_data.symbols import normalize_symbol, get_symbol_meta
from backend.market_data.yahoo_provider import market_data_provider
from backend.analytics.indicators import calculate_technical_indicators, get_latest_indicators_summary
from backend.ml.pipeline import train_and_predict
from backend.trading.backtest import run_ma_crossover_backtest
from backend.trading.paper_trading import paper_trading_engine
from backend.analytics.risk import calculate_portfolio_risk

logger = logging.getLogger("quantex.tools")

def tool_fetch_stock_data(symbol: str, period: str = "1M") -> dict:
    """Fetches quote snapshot and historical data status for an Indian equity."""
    norm = normalize_symbol(symbol)
    quote = market_data_provider.get_quote(norm)
    return {
        "tool": "fetch_stock_data",
        "symbol": norm,
        "quote": quote
    }

def tool_calculate_indicators(symbol: str, period: str = "6M") -> dict:
    """Calculates all institutional technical indicators for an Indian equity."""
    norm = normalize_symbol(symbol)
    df, status_meta = market_data_provider.get_historical_data(norm, period=period)
    df_ind = calculate_technical_indicators(df)
    summary = get_latest_indicators_summary(df_ind)
    return {
        "tool": "calculate_indicators",
        "symbol": norm,
        "indicators": summary,
        "data_status": status_meta
    }

def tool_generate_ml_prediction(symbol: str, model_type: str = "logistic_regression", horizon: int = 5) -> dict:
    """Generates directional machine learning prediction over specified horizon."""
    norm = normalize_symbol(symbol)
    df, _ = market_data_provider.get_historical_data(norm, period="1Y")
    pred = train_and_predict(df, model_type=model_type, horizon=horizon)
    return {
        "tool": "generate_ml_prediction",
        "symbol": norm,
        "prediction": pred
    }

def tool_explain_stock_analysis(symbol: str) -> dict:
    """Aggregates quote, indicators, and ML prediction into a structured analysis packet."""
    norm = normalize_symbol(symbol)
    quote = market_data_provider.get_quote(norm)
    df, _ = market_data_provider.get_historical_data(norm, period="1Y")
    df_ind = calculate_technical_indicators(df)
    indicators = get_latest_indicators_summary(df_ind)
    ml_res = train_and_predict(df, model_type="logistic_regression", horizon=5)
    
    return {
        "tool": "explain_stock_analysis",
        "symbol": norm,
        "quote": quote,
        "indicators": indicators,
        "prediction": ml_res
    }

def tool_run_backtest(symbol: str, fast_period: int = 20, slow_period: int = 50, initial_capital: float = 1000000.0) -> dict:
    """Runs moving average crossover backtest simulation on historical equity data."""
    norm = normalize_symbol(symbol)
    df, _ = market_data_provider.get_historical_data(norm, period="1Y")
    res = run_ma_crossover_backtest(df, fast_period=fast_period, slow_period=slow_period, initial_capital=initial_capital)
    return {
        "tool": "run_backtest",
        "symbol": norm,
        "backtest": res
    }

def tool_get_portfolio() -> dict:
    """Retrieves current virtual paper trading portfolio balance, holdings, and P&L."""
    port = paper_trading_engine.get_portfolio()
    return {
        "tool": "get_portfolio",
        "portfolio": port
    }

def tool_calculate_risk_metrics() -> dict:
    """Computes portfolio risk exposure, concentration, volatility, and stress-tests."""
    risk = calculate_portfolio_risk()
    return {
        "tool": "calculate_risk_metrics",
        "risk_analytics": risk
    }

def tool_get_market_overview() -> dict:
    """Retrieves broad market performance across Indian equity watchlist."""
    quotes = market_data_provider.get_watchlist_overview()
    advances = sum(1 for q in quotes if q.get("change", 0) > 0)
    declines = sum(1 for q in quotes if q.get("change", 0) < 0)
    unchanged = len(quotes) - advances - declines
    return {
        "tool": "get_market_overview",
        "total_equities": len(quotes),
        "advances": advances,
        "declines": declines,
        "unchanged": unchanged,
        "market_breadth": f"{advances} Advances / {declines} Declines",
        "watchlist_sample": [
            {
                "symbol": q["symbol"],
                "ticker": q.get("ticker", ""),
                "price": q.get("price", 0.0),
                "change_pct": q.get("change_pct", 0.0),
                "status": q.get("status", "")
            }
            for q in quotes[:5]
        ]
    }

def tool_get_transaction_history(limit: int = 20) -> dict:
    """Fetches virtual paper trading transaction records."""
    txns = paper_trading_engine.get_transactions(limit=limit)
    return {
        "tool": "get_transaction_history",
        "transactions": txns
    }

APPROVED_TOOLS = {
    "fetch_stock_data": tool_fetch_stock_data,
    "calculate_indicators": tool_calculate_indicators,
    "generate_ml_prediction": tool_generate_ml_prediction,
    "explain_stock_analysis": tool_explain_stock_analysis,
    "run_backtest": tool_run_backtest,
    "get_portfolio": tool_get_portfolio,
    "calculate_risk_metrics": tool_calculate_risk_metrics,
    "get_transaction_history": tool_get_transaction_history,
    "get_market_overview": tool_get_market_overview
}
