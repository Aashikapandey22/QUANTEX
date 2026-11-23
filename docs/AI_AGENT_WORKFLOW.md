# AUTONOMOUS AI AGENT WORKFLOW

## Cognitive Architecture: PLAN → ACT → OBSERVE → RESPOND

QUANTEX implements an institutional tool-using autonomous AI agent. Rather than functioning as a free-form chatbot, the agent follows a formal 4-phase cognitive loop:

```
[ Natural Language Query ]
            │
            ▼
┌───────────────────────┐
│       1. PLAN         │  Extract intent & stock symbols.
│                       │  Select required tools from approved allowlist.
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│       2. ACT          │  Execute allowlisted backend functions.
│                       │  Pass strictly validated parameters.
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│     3. OBSERVE        │  Inspect tool outputs and verify integrity.
│                       │  Detect errors, missing data, or boundary violations.
└───────────┬───────────┘
            │
            ▼
┌───────────────────────┐
│      4. RESPOND       │  Synthesize verified factual findings using Gemini
│                       │  (or internal institutional quantitative fallback).
└───────────────────────┘
```

---

## Approved Backend Tools Allowlist

| Tool Name | Parameters | Purpose |
|---|---|---|
| `fetch_stock_data` | `symbol`, `period` | Retrieves real-time quote snapshot & market status |
| `calculate_indicators` | `symbol`, `period` | Calculates SMA, EMA, RSI, MACD, BB, ATR, Volatility |
| `generate_ml_prediction` | `symbol`, `model_type`, `horizon` | Executes chronological ML directional forecast |
| `explain_stock_analysis` | `symbol` | Aggregates quote, indicators, and ML metrics |
| `run_backtest` | `symbol`, `fast_period`, `slow_period` | Simulates SMA crossover strategy with costs |
| `get_portfolio` | None | Queries virtual cash, active holdings, and P&L |
| `calculate_risk_metrics`| None | Computes portfolio exposure, HHI, and 95% VaR |
| `get_transaction_history`| `limit` | Retrieves chronological virtual trade logs |

---

## Security Safeguards

- **Strict Allowlist**: Tools are registered in a Python dictionary. Any attempt to invoke arbitrary functions, `eval`, or shell commands is immediately rejected.
- **Argument Sanitization**: Stock symbols are normalized through `normalize_symbol()`, and integers are bounded.
- **Audit Logging**: Every agent interaction (user query, plan steps, tools called, observations, and status) is persisted in the `agent_logs` SQLite table.
