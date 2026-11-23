# REST API DOCUMENTATION

Base URL: `http://127.0.0.1:5001/api`

---

### 1. System Health
- **Endpoint**: `GET /health`
- **Response**:
```json
{
  "status": "healthy",
  "database_connected": true,
  "gemini_configured": false,
  "gemini_model": "Local Rule Engine",
  "virtual_trading_mode": "ACTIVE (Strict Virtual Money Only)",
  "timestamp": "2026-11-23T05:10:00Z"
}
```

---

### 2. Market Watchlist
- **Endpoint**: `GET /watchlist`
- **Response**: Array of 10 Indian equities with price, day change, high, low, volume, and data status.

---

### 3. Stock Candlestick History
- **Endpoint**: `GET /stock/<symbol>/history?period=1M|3M|6M|1Y`
- **Response**:
```json
{
  "success": true,
  "symbol": "RELIANCE.NS",
  "period": "1Y",
  "count": 252,
  "status_meta": { "status": "sample", "last_market_date": "2026-11-20" },
  "candles": [
    { "date": "2026-11-20", "open": 2975.0, "high": 2990.0, "low": 2965.0, "close": 2980.5, "volume": 1200000 }
  ]
}
```

---

### 4. Technical Indicators
- **Endpoint**: `GET /stock/<symbol>/indicators?period=6M`
- **Response**: Summary of SMA 20/50, EMA 20, RSI 14, MACD, Bollinger Bands, ATR 14, Volatility, and time series arrays for chart overlays.

---

### 5. Machine Learning Prediction
- **Endpoint**: `GET /stock/<symbol>/prediction?model=logistic_regression&horizon=5`
- **Response**: Predicted direction (`Bullish`/`Bearish`/`Neutral`), confidence score, out-of-sample accuracy, precision, recall, and features used.

---

### 6. AI Agent Natural Language Execution
- **Endpoint**: `POST /agent/command`
- **Payload**: `{"command": "Analyse TCS"}`
- **Response**: Full telemetry (`plan`, `act`, `observe`) and synthesized institutional `response`.

---

### 7. Strategy Backtest
- **Endpoint**: `POST /backtest`
- **Payload**: `{"symbol": "TCS.NS", "fast_period": 20, "slow_period": 50, "initial_capital": 1000000.0}`
- **Response**: Total return %, CAGR, Max drawdown, Sharpe ratio, win rate, trades array, and equity curve.

---

### 8. Virtual Paper Trading
- `GET /trading/portfolio`: Cash, holdings, unrealized and realized P&L.
- `POST /trading/order`: Execute virtual BUY/SELL (`{"symbol": "INFY.NS", "side": "BUY", "quantity": 10}`).
- `GET /trading/transactions`: Chronological ledger of executed virtual trades.
- `GET /trading/risk`: Portfolio risk rating, exposure %, HHI concentration, 95% VaR, and stress-test scenarios.
- `POST /trading/reset`: Resets virtual cash balance back to INR 10,00,000.
