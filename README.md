# QUANTEX – AI-Powered Trading Intelligence & Institutional Terminal

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Flask 3.1](https://img.shields.io/badge/flask-3.1-black.svg)](https://palletsprojects.com/p/flask/)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg)](LICENSE)
[![Tests: 44 Passed](https://img.shields.io/badge/tests-44%20passed-brightgreen.svg)](tests/)

**QUANTEX** is an institutional-grade stock market analysis, quantitative forecasting, autonomous AI agent, and virtual paper trading platform specifically engineered for Indian Equities on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE).

---

## 🏛 Platform Overview

QUANTEX is designed from the ground up as a high-density, low-latency financial terminal. It combines deterministic quantitative modeling, machine learning with rigorous chronological splits, an autonomous tool-orchestrating AI agent, and a virtual paper trading simulator backed by an institutional risk management suite.

---

## ✨ Key Features & Architecture

### 1. Institutional Design System
- **Dark Terminal Theme**: Deep charcoal (`#090C10`), graphite panels, ivory typography, emerald (`#10B981`) bullish values, and ruby (`#F43F5E`) bearish accents.
- **High-Density Layout**: 9 navigation panels including Market Overview, Watchlist, Candlestick Charting, AI Predictions, AI Analyst, Technical Indicators, Strategy Backtesting, Paper Trading, and Risk Management.

### 2. Market Data Integration
- **Yahoo Finance (`yfinance`) Provider**: Automated ingestion of daily OHLCV bars for top Indian benchmark equities (`RELIANCE.NS`, `TCS.NS`, `INFY.NS`, `HDFCBANK.NS`, `ICICIBANK.NS`, `SBIN.NS`, `ITC.NS`, `LT.NS`, `TATAMOTORS.NS`, `BHARTIARTL.NS`).
- **Resilient Caching & Offline Generation**: SQLite-backed TTL caching (300s) with rate-limit protection and deterministic Geometric Brownian Motion fallback if live feeds are unreachable.

### 3. Institutional Technical Analytics
- Pure Pandas and NumPy calculations of:
  - **Moving Averages**: 20-day SMA, 50-day SMA, 20-day EMA
  - **Momentum Oscillators**: RSI (14-period), MACD (12, 26, 9) with signal line and histogram
  - **Volatility & Bands**: Bollinger Bands (20-day, 2σ), Average True Range (ATR 14), 20-day Annualized Historical Volatility

### 4. Rigorous Machine Learning Pipeline
- **Zero Look-Ahead Bias**: Strict chronological 80/20 train/test split (no random shuffling).
- **Target Formulation**: Directional classification estimating 5-day future price change: $C_{t+5} > C_t$.
- **Fair Dual-Model Comparison**: Logistic Regression baseline paired with Random Forest on the identical test split.
- **Complete Metric Separation**: Clearly separates predicted direction, raw class probabilities, directional score ($[-100, +100]$), out-of-sample accuracy, precision, recall, F1, confusion matrix, and majority-class baseline.
- **Reliability Indicator**: Triggers explicit warnings when test accuracy falls below naive baselines.

### 5. Autonomous Tool-Using AI Agent
- **9-Stage Cognitive Loop**:
  $$\text{User Input} \to \text{Entity Extraction} \to \text{Symbol Validation} \to \text{Intent Classification} \to \text{Plan} \to \text{Tool Selection} \to \text{Act} \to \text{Observe} \to \text{Respond}$$
- **10 Distinct Intents Handled**: `GREETING`, `GENERAL_QUESTION`, `STOCK_ANALYSIS`, `PREDICTION`, `INDICATOR_EXPLANATION`, `COMPARISON`, `INVESTMENT_QUESTION`, `BACKTEST`, `PORTFOLIO`, `UNKNOWN`.
- **Strict Financial Safety**:
  - Greetings and general queries execute zero stock tools.
  - Ambiguous investment queries prompt for asset clarification without running tools or fabricating prices.
  - Ordinary English words (`SHOULD`, `BUY`, `CAN`, `WILL`, `THE`) are blacklisted from being converted into tickers.
  - Only registered backend tools execute inside a sandboxed runner.

### 6. Quantitative Strategy Backtester
- Moving Average Crossover simulation (SMA 20 / SMA 50).
- Strict next-bar execution modeling with 0.10% transaction fees and 0.05% slippage.
- Computes CAGR, Sharpe Ratio, Maximum Drawdown, and Win Rate with equity curve telemetry.

### 7. Virtual Paper Trading & Risk Management
- **Simulated Capital**: Starts with ₹10,00,000 in virtual trading capital.
- **Execution Controls**: Real-time cash validation, oversell protection, and weighted-average price tracking.
- **Institutional Risk Suite**: Herfindahl-Hirschman Index (HHI) concentration auditing, 1-Day 95% Parametric Value at Risk (VaR), and stress-test scenarios (-2%, -5%, -10%).

### 8. Browser Voice Assistant
- Web Speech API integration (`SpeechRecognition` & `SpeechSynthesis`) for hands-free queries (e.g. *"Analyse TCS"* or *"Show my paper trading portfolio"*).

---

## 🛠 Technology Stack

| Layer | Technologies |
|:---|:---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (ES6+), Chart.js, HTML5 Canvas 2D, Web Speech API |
| **Backend** | Python 3.10+ (Tested on Python 3.14), Flask 3.1, REST APIs |
| **Machine Learning** | Scikit-learn, Pandas, NumPy |
| **Market Data** | yfinance, SQLite Caching, Geometric Brownian Motion |
| **AI Integration** | Google GenAI SDK (`gemini-2.5-flash`), Sandboxed Tool Agent |
| **Database** | SQLite3 (Thread-safe connection pool) |
| **Testing** | Pytest 8.4 (44 Automated Unit & Integration Tests) |

---

## 🚀 Installation & Local Setup

### 1. Clone the Repository
```bash
git clone https://github.com/<your-username>/QUANTEX-ANTIGRAVITY.git
cd QUANTEX-ANTIGRAVITY
```

### 2. Create and Activate Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies
```bash
python3 -m pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the template configuration file:
```bash
cp .env.example .env
```
Open `.env` and review the settings:
```ini
FLASK_ENV=production
FLASK_DEBUG=0
SECRET_KEY=quantex-secure-key-replace-in-production

# Google Gemini API (Optional: If omitted, QUANTEX runs seamlessly using its local quantitative engine)
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.5-flash

# Virtual Paper Trading Initial Capital (INR 10,00,000)
INITIAL_CAPITAL=1000000.0
TRANSACTION_FEE_PCT=0.001
SLIPPAGE_PCT=0.0005
CACHE_TTL_SECONDS=300
```
> [!NOTE]
> Setting `GEMINI_API_KEY` is completely optional. When omitted or offline, QUANTEX runs locally with its deterministic institutional quantitative rule engine.

### 5. Run Automated Tests
Verify all 44 unit and integration tests pass:
```bash
python3 -m pytest -v
```

### 6. Launch the Application
```bash
python3 app.py
```
Open your browser and navigate to:
**`http://127.0.0.1:5001`**

---

## 📸 Screenshots & Interface Walkthrough

```
+---------------------------------------------------------------------------------------+
|  QUANTEX  |  Search Equities [       ]  |  NSE FEED: ACTIVE  |  CAPITAL: ₹9,72,703.13  |
+---------------------------------------------------------------------------------------+
| Overview | Markets | AI Predictions | AI Analyst | Analytics | Backtesting | Risk ... |
+---------------------------------------------------------------------------------------+
|                                                                                       |
|  [ RELIANCE.NS ₹3,289.02 ]   [ 1M | 3M | 6M | 1Y ]                                    |
|  +---------------------------------------------------------------------------------+  |
|  |     HIGH-DPI CANDLESTICK & VOLUME CHART (SMA 20, SMA 50, EMA 20 OVERLAYS)       |  |
|  +---------------------------------------------------------------------------------+  |
|                                                                                       |
|  +---------------------------+  +--------------------------------------------------+  |
|  | WATCHLIST (NSE 10)        |  | AI PREDICTION & RELIABILITY CARD                 |  |
|  | - RELIANCE.NS (+1.42%)    |  | Direction: BULLISH | P(Bull): 62.5%              |  |
|  | - TCS.NS      (-0.64%)    |  | Test Accuracy: 42.25% | Baseline: 42.25%         |  |
|  | - INFY.NS     (+0.85%)    |  | Reliability: LOW (Academic Estimate Only)        |  |
|  +---------------------------+  +--------------------------------------------------+  |
+---------------------------------------------------------------------------------------+
| [✦ AI Terminal]  PLAN -> ACT -> OBSERVE -> RESPOND Cognitive Loop Execution Drawer     |
+---------------------------------------------------------------------------------------+
```

---

## 💬 AI Agent Demonstration Commands

QUANTEX features an autonomous cognitive agent in the slide-out AI Terminal. Try these ten verified commands:

1. `hello` — Friendly greeting and platform capability overview (0 tools executed).
2. `What can you do?` — Institutional platform architecture explanation (0 tools executed).
3. `Should I invest?` — Ambiguous query handling; prompts user to specify a stock without hallucinating prices.
4. `Analyse TCS` — Executes full price action, indicator, and ML forecast for `TCS.NS`.
5. `Predict RELIANCE for 5 trading days` — Executes 5-day ML pipeline with baseline comparison.
6. `Explain RSI of INFY` — Computes 14-period RSI and explains momentum consolidation.
7. `Compare TCS and INFY` — Executes dual-stock analysis and renders comparative side-by-side table.
8. `Backtest the moving average strategy` — Simulates SMA 20/50 crossover with fees and slippage.
9. `Show my paper trading portfolio` — Queries virtual ledger and calculates 95% Parametric VaR.
10. `Analyse INVALIDXYZ` — Rejects unverified ticker cleanly without fabricating market prices.

---

## 📁 Repository Directory Structure

```
QUANTEX-ANTIGRAVITY/
├── .env.example                # Safe environment variables template
├── .gitignore                  # Security-hardened gitignore
├── README.md                   # Complete documentation
├── requirements.txt            # Python dependencies
├── app.py                      # Flask application entry point (Port 5001)
├── config.py                   # Centralized application configuration
├── backend/
│   ├── database.py             # SQLite thread-safe database manager
│   ├── market_data/
│   │   ├── base.py             # MarketDataProvider abstract base class
│   │   ├── symbols.py          # NSE registry and English words blacklist
│   │   └── yahoo_provider.py   # Yahoo Finance adapter with SQLite cache
│   ├── analytics/
│   │   ├── indicators.py       # Technical indicator calculation engine
│   │   └── risk.py             # HHI concentration and Parametric VaR
│   ├── ml/
│   │   └── pipeline.py         # Chronological ML classification pipeline
│   ├── trading/
│   │   ├── backtest.py         # SMA crossover backtesting engine
│   │   └── paper_trading.py    # Virtual order execution and ledger
│   ├── agents/
│   │   ├── gemini_analyst.py   # Google GenAI SDK integration & local engine
│   │   ├── tools.py            # Approved tool execution registry
│   │   └── tool_agent.py       # 9-stage cognitive autonomous agent
│   └── routes/
│       └── api.py              # REST API blueprint routes
├── frontend/
│   ├── templates/
│   │   └── index.html          # High-density institutional terminal template
│   └── static/
│       ├── css/
│       │   └── styles.css      # Institutional trading terminal styling
│       └── js/
│           ├── api.js          # REST client wrapper
│           ├── app.js          # Main terminal application controller
│           ├── charts.js       # Canvas 2D candlestick charting engine
│           ├── agent_ui.js     # Cognitive loop telemetry drawer manager
│           └── voice.js        # Browser Web Speech API assistant
├── docs/                       # Comprehensive academic & architecture docs
│   ├── AI_AGENT_WORKFLOW.md
│   ├── API_DOCUMENTATION.md
│   ├── DEMO_GUIDE.md
│   ├── MARKET_DATA_SOURCES.md
│   ├── ML_METHODOLOGY.md
│   ├── PROJECT_ARCHITECTURE.md
│   ├── TESTING_REPORT.md
│   └── VIVA_QUESTIONS.md
└── tests/                      # Automated test suite (Pytest)
    ├── test_agent.py
    ├── test_api.py
    ├── test_backtest.py
    ├── test_indicators.py
    ├── test_market_data.py
    ├── test_ml_pipeline.py
    └── test_paper_trading.py
```

---

## 🔒 Security & Data Integrity

- **Zero Hardcoded Secrets**: All configuration is ingested dynamically via `config.py` from `.env` or system environment.
- **Git Protection**: `.env`, `.venv`, `__pycache__`, local database files (`data/*.db`), and temporary files are strictly ignored.
- **Sandboxed Execution**: Agent tools execute only pre-approved internal functions. Dynamic code execution (`exec()`, `eval()`, shell calls) is strictly prohibited.

---

## ⚠️ Academic & Educational Disclaimer

> **IMPORTANT NOTICE**:
> QUANTEX is an educational, research, and algorithmic simulation platform.
> It **NEVER** connects to real broker order-placement APIs and **NEVER** executes real-money trades.
> All financial operations, balances, trades, and portfolios represent strictly simulated virtual capital.
> Machine learning predictions and quantitative indicators are for academic demonstration and do not constitute financial advice.

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
