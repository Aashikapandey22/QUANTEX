# PROJECT ARCHITECTURE & SYSTEM DESIGN

## 1. High-Level Architectural Overview

QUANTEX is structured into modular layers with clear separation of responsibilities:

```
QUANTEX/
├── app.py                      # Flask Application Factory & Server Entry
├── config.py                   # Centralized Configuration & Environment Settings
├── requirements.txt            # Python Package Dependencies
├── .env.example                # Template for User Credentials
├── backend/
│   ├── database.py             # SQLite Connection Pool & Schema DDL
│   ├── routes/
│   │   └── api.py              # REST API Endpoints Definition
│   ├── market_data/
│   │   ├── base.py             # Abstract MarketDataProvider Interface
│   │   ├── symbols.py          # Watchlist Metadata & NSE Registry
│   │   └── yahoo_provider.py   # Yahoo Finance Adapter + SQLite Cache + Fallback
│   ├── analytics/
│   │   ├── indicators.py       # Quantitative Technical Indicators Engine
│   │   └── risk.py             # Risk Management & Stress-Testing Engine
│   ├── ml/
│   │   └── pipeline.py         # Chronological Train/Test ML Pipeline
│   ├── trading/
│   │   ├── paper_trading.py    # Virtual Portfolio & Order Execution Engine
│   │   └── backtest.py         # Strategy Backtester (Next-Bar Execution)
│   └── agents/
│       ├── gemini_analyst.py   # Google GenAI Integration + Local Quant Fallback
│       ├── tools.py            # Sandboxed Allowlisted Tool Registry
│       └── tool_agent.py       # Autonomous PLAN -> ACT -> OBSERVE -> RESPOND Agent
├── frontend/
│   ├── templates/
│   │   └── index.html          # Institutional Terminal Layout
│   └── static/
│       ├── css/styles.css      # Institutional Design System
│       └── js/
│           ├── api.js          # REST Client with Timeouts
│           ├── charts.js       # HTML5 Canvas Candlestick & Volume Chart
│           ├── voice.js        # Web Speech API Speech-to-Text & Text-to-Speech
│           ├── agent_ui.js     # Autonomous Agent Telemetry & Chat Drawer
│           └── app.js          # Main Application Orchestrator
├── tests/                      # Automated Pytest Suite (31 Tests)
└── docs/                       # Technical Specifications & Guides
```

---

## 2. Core Architectural Principles

1. **Provider Abstraction**: Market data ingestion implements an abstract base class (`MarketDataProvider`), decoupling the core engine from Yahoo Finance.
2. **Ground-Truth Preservation**: AI components receive structured, verified factual data from the backend. LLMs are never permitted to fabricate financial quotes or dates.
3. **Zero Look-Ahead Bias**: ML feature engineering and backtest engines strictly enforce chronological execution without future data leakage.
4. **Resilient Local Fallbacks**: If external network connectivity or paid APIs are unavailable, internal high-fidelity deterministic quantitative models maintain full application functionality.
5. **Simulated Sandboxing**: Virtual paper trading isolates order logic from real broker APIs, ensuring no real money is ever at risk.
