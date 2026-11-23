# COMPREHENSIVE VIVA & INTERVIEW QUESTIONS

### Q1: What is the primary objective of QUANTEX?
**Answer:** QUANTEX is an institutional AI-powered Indian equity market intelligence and paper trading platform. It combines real market data, mathematical technical indicators, machine-learning-based directional forecasting, an autonomous tool-using AI Agent, strategy backtesting, and virtual paper trading to educate quantitative analysts without risking real capital.

---

### Q2: Why is random shuffling prohibited in time-series machine learning?
**Answer:** In cross-sectional data, random shuffling is standard. However, in financial time series, prices exhibit temporal dependency and autocorrelation. Random shuffling causes **look-ahead bias** and **temporal data leakage**, where future prices leak into training sets. In QUANTEX, we strictly enforce **chronological train/test splitting** (first 80% train, last 20% test).

---

### Q3: What features did you engineer for the ML classification pipeline?
**Answer:** Raw prices are non-stationary and cannot be fed directly into classifiers. We engineer 11 stationary relative ratios:
1. 1-day & 5-day percentage return lags
2. Moving average distance ratios ($C_t / \text{SMA}_{20} - 1$, $C_t / \text{SMA}_{50} - 1$, $C_t / \text{EMA}_{20} - 1$)
3. Wilder's Normalized RSI (14)
4. Price-scaled MACD & MACD Histogram
5. Normalized Average True Range (ATR / Price)
6. 20-day annualized rolling volatility
7. Relative volume ratio ($V_t / \text{SMA}_{20}(V)$)

---

### Q4: Explain the cognitive loop of the QUANTEX AI Agent.
**Answer:** The agent implements a formal 4-stage cycle:
1. **PLAN**: Natural language parsing extracts intent and stock symbols, selecting approved tools from a strict allowlist.
2. **ACT**: Sandboxed backend execution of allowlisted tools (e.g. `calculate_indicators`, `generate_ml_prediction`).
3. **OBSERVE**: Verification of returned datasets, boundary checks, and error detection.
4. **RESPOND**: Factual synthesis of ground-truth findings using Google Gemini or the internal institutional rule engine.

---

### Q5: How do you prevent arbitrary code execution or LLM hallucinations?
**Answer:** 
- **Security**: The agent has an immutable dictionary of approved tools. It never executes `eval()`, `exec()`, or arbitrary shell commands.
- **Hallucination Prevention**: Gemini only receives verified, pre-computed quantitative numbers from the backend. The prompt explicitly restricts the model to the factual data packet.

---

### Q6: How does the strategy backtester avoid look-ahead bias?
**Answer:** A common backtesting error is executing trades on the same bar a crossover signal occurs using that bar's closing price. In real markets, the close is only known at market close. QUANTEX enforces **next-bar execution**: signals detected at bar $t$ execute on bar $t+1$ at that bar's price, with realistic slippage (0.05%) and brokerage fees (0.1%).

---

### Q7: How is portfolio risk evaluated in the paper trading module?
**Answer:** We evaluate risk across three dimensions:
1. **Concentration**: Herfindahl-Hirschman Index ($\text{HHI} = \sum w_i^2$) to detect over-concentration in single equities.
2. **Value at Risk (VaR)**: 1-Day 95% Parametric VaR computed using weighted volatility: $\text{VaR}_{95} = \text{Portfolio Value} \times 1.645 \times \sigma_{\text{daily}}$.
3. **Stress Testing**: Deterministic impact analysis of $-2\%$, $-5\%$, and $-10\%$ systemic drawdowns on active holdings.
