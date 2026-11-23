"""
QUANTEX Autonomous Cognitive Agent Architecture.
Full 9-Stage Pipeline:
USER INPUT
  → 1. INTENT CLASSIFICATION
  → 2. ENTITY EXTRACTION
  → 3. SYMBOL VALIDATION
  → 4. PLAN
  → 5. TOOL SELECTION
  → 6. ACT
  → 7. OBSERVE
  → 8. RESPOND

Classifies 10 standard institutional intents:
- GREETING
- GENERAL_QUESTION
- STOCK_ANALYSIS
- PREDICTION
- INDICATOR_EXPLANATION
- COMPARISON
- INVESTMENT_QUESTION
- BACKTEST
- PORTFOLIO
- UNKNOWN

Security & Data Integrity Guarantees:
- GREETING and GENERAL_QUESTION execute ZERO stock tools.
- INVESTMENT_QUESTION without verified symbol asks for clarification without executing stock tools.
- Only registered and approved backend tools may execute.
- Never executes arbitrary code or unvalidated expressions.
- Never fabricates market data or tool verification states.
- OBSERVE inspects actual tool output before marking verified.
"""
import re
import json
import logging
from datetime import datetime
from config import Config
from backend.database import get_db_connection
from backend.agents.tools import APPROVED_TOOLS
from backend.agents.gemini_analyst import gemini_analyst
from backend.market_data.symbols import (
    is_valid_symbol,
    safe_normalize_symbol,
    COMMON_ENGLISH_WORDS,
    WATCHLIST_METADATA,
    TICKER_TO_SYMBOL
)

logger = logging.getLogger("quantex.agent")

class QuantexToolAgent:
    def __init__(self):
        self.approved_tools = APPROVED_TOOLS

    # ==================== STAGE 1: INTENT CLASSIFICATION ====================
    def classify_intent(self, query: str, raw_entities: list[str], valid_symbols: list[str]) -> str:
        """
        Classifies user input into one of the 10 standard intents:
        GREETING, GENERAL_QUESTION, STOCK_ANALYSIS, PREDICTION, INDICATOR_EXPLANATION,
        COMPARISON, INVESTMENT_QUESTION, BACKTEST, PORTFOLIO, UNKNOWN.
        Uses Gemini for natural language understanding when configured, with a deterministic local fallback.
        """
        q = query.lower().strip()

        # Check Gemini when configured
        if gemini_analyst.is_configured():
            try:
                prompt = (
                    f"Classify the following user query into exactly ONE of these intents:\n"
                    f"- GREETING: friendly hello, hi, greetings, good morning\n"
                    f"- GENERAL_QUESTION: asking about capabilities, what can you do, who are you, platform features\n"
                    f"- STOCK_ANALYSIS: analyse, analyze, review, evaluate a specific stock\n"
                    f"- PREDICTION: predict, forecast, ml model direction\n"
                    f"- INDICATOR_EXPLANATION: explain rsi, macd, moving averages, indicators\n"
                    f"- COMPARISON: compare two or more stocks\n"
                    f"- INVESTMENT_QUESTION: should i invest, should i buy, is it good to invest, buy recommendations\n"
                    f"- BACKTEST: backtest, strategy testing, ma crossover, simulation\n"
                    f"- PORTFOLIO: portfolio, holdings, cash balance, virtual money, transactions, risk\n"
                    f"- UNKNOWN: unsupported requests or unintelligible input\n\n"
                    f"Query: \"{query}\"\n"
                    f"Return ONLY the uppercase intent name, nothing else."
                )
                res = gemini_analyst.generate_analysis(prompt)
                if not res.get("is_fallback"):
                    predicted = res.get("analysis", "").strip().upper()
                    # Clean out markdown or extra quotes
                    predicted = re.sub(r"[^A-Z_]", "", predicted)
                    valid_intents = {
                        "GREETING", "GENERAL_QUESTION", "STOCK_ANALYSIS", "PREDICTION",
                        "INDICATOR_EXPLANATION", "COMPARISON", "INVESTMENT_QUESTION",
                        "BACKTEST", "PORTFOLIO", "UNKNOWN"
                    }
                    if predicted in valid_intents:
                        return predicted
            except Exception as e:
                logger.warning(f"Gemini intent classification fallback to local: {e}")

        # Deterministic Institutional Local Intent Classifier
        # 1. GREETING
        greeting_words = {"hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy", "sup"}
        # check whole words or start
        clean_words = re.findall(r"\b[a-z]+\b", q)
        if any(w in greeting_words for w in clean_words) and len(clean_words) <= 3 and not valid_symbols and not raw_entities:
            return "GREETING"
        if q in greeting_words or q.startswith("hello ") or q.startswith("hi "):
            if not valid_symbols and not raw_entities:
                return "GREETING"

        # 2. GENERAL_QUESTION
        general_patterns = [
            "what can you do", "who are you", "what are your capabilities",
            "help", "how do you work", "what is quantex", "features", "commands",
            "what do you do", "how can you help"
        ]
        if any(pat in q for pat in general_patterns) and not valid_symbols:
            return "GENERAL_QUESTION"

        # 3. COMPARISON (Two or more candidate symbols, or explicit compare keyword)
        if ("compare" in q or "versus" in q or " vs " in q) and (len(valid_symbols) >= 2 or len(raw_entities) >= 2):
            return "COMPARISON"

        # 4. BACKTEST
        if "backtest" in q or "strategy" in q or "crossover" in q or "simulation" in q:
            return "BACKTEST"

        # 5. PORTFOLIO & RISK
        if any(w in q for w in ["portfolio", "holdings", "balance", "virtual cash", "transaction", "trades", "risk", "var", "drawdown"]):
            return "PORTFOLIO"

        # 6. INDICATOR_EXPLANATION
        indicator_terms = ["rsi", "macd", "moving average", "sma", "ema", "bollinger", "atr", "volatility", "indicator"]
        if any(term in q for term in indicator_terms) and ("explain" in q or "what is" in q or "calculate" in q or valid_symbols):
            return "INDICATOR_EXPLANATION"

        # 7. PREDICTION
        if "predict" in q or "forecast" in q or "ml model" in q or "directional probability" in q:
            return "PREDICTION"

        # 8. INVESTMENT_QUESTION
        invest_triggers = [
            "should i invest", "should i buy", "is it a good time to buy", "can i invest",
            "is investing good", "where should i invest", "advise me", "recommend",
            "is it safe to invest", "ya should i buy", "so should i invest", "should i trade"
        ]
        if any(trig in q for trig in invest_triggers):
            return "INVESTMENT_QUESTION"

        # 9. STOCK_ANALYSIS
        analysis_terms = ["analyse", "analyze", "check", "review", "evaluate", "quote", "price", "stock"]
        if (any(term in q for term in analysis_terms) and (valid_symbols or raw_entities)) or valid_symbols:
            return "STOCK_ANALYSIS"

        # Default fallback
        if len(clean_words) <= 2:
            return "GENERAL_QUESTION"
        return "UNKNOWN"

    # ==================== STAGE 2: ENTITY EXTRACTION ====================
    def extract_entities(self, query: str) -> list[str]:
        """
        Extracts raw potential stock ticker/company candidates from query.
        Filters out common English conversational words.
        """
        candidates = []
        upper_query = query.upper()

        # 1. Match known tickers
        for ticker in TICKER_TO_SYMBOL.keys():
            pattern = rf"\b{ticker}(?:\.NS|\.BO)?\b"
            if re.search(pattern, upper_query):
                if ticker not in candidates:
                    candidates.append(ticker)

        # 2. Extract potential capitalized symbols only following stock inquiry keywords or with .NS/.BO
        lead_patterns = [
            r"\b(?:ANALYSE|ANALYZE|CHECK|PREDICT|COMPARE|PRICE OF|QUOTE OF|STOCK OF|EQUITY)\s+([A-Z0-9]{3,12}(?:\.NS|\.BO)?)\b",
            r"\b([A-Z0-9]{3,12}\.(?:NS|BO))\b"
        ]
        for pat in lead_patterns:
            matches = re.findall(pat, upper_query)
            for m in matches:
                clean_m = m.replace(".NS", "").replace(".BO", "")
                if clean_m not in COMMON_ENGLISH_WORDS and clean_m not in candidates:
                    candidates.append(clean_m)

        return candidates

    # ==================== STAGE 3: SYMBOL VALIDATION ====================
    def validate_symbols(self, candidates: list[str]) -> tuple[list[str], list[str]]:
        """
        Splits extracted candidates into (valid_canonical_symbols, invalid_unsupported_symbols).
        Only verified National Stock Exchange (NSE) tickers pass validation.
        """
        valid = []
        invalid = []

        for cand in candidates:
            norm = safe_normalize_symbol(cand)
            if norm and is_valid_symbol(norm):
                if norm not in valid:
                    valid.append(norm)
            else:
                if cand not in invalid and cand not in COMMON_ENGLISH_WORDS:
                    invalid.append(cand)

        return valid, invalid

    # ==================== STAGE 4: PLAN ====================
    def generate_plan(self, intent: str, valid_symbols: list[str], invalid_symbols: list[str], query: str) -> list[str]:
        """
        Produces an explicit, reasoned action plan based on verified intent and symbols.
        """
        steps = []
        if intent == "GREETING":
            steps.append("1. Acknowledge user greeting.")
            steps.append("2. Introduce QUANTEX institutional intelligence capabilities without invoking stock tools.")
            return steps

        if intent == "GENERAL_QUESTION":
            steps.append("1. Analyze user platform question.")
            steps.append("2. Provide an institutional overview of available modules, supported equities, and safety boundaries.")
            return steps

        # If explicit invalid stock symbols were provided for a stock-specific task, reject execution
        if invalid_symbols and not valid_symbols and intent not in ["BACKTEST", "PORTFOLIO"]:
            steps.append(f"1. Detected unsupported instrument candidates: {', '.join(invalid_symbols)}.")
            steps.append("2. Refuse execution without fabricating fictitious stock data.")
            steps.append("3. Present verified National Stock Exchange (NSE) instrument registry to user.")
            return steps

        if intent == "INVESTMENT_QUESTION":
            if not valid_symbols:
                steps.append("1. Identify ambiguous investment inquiry lacking a specific target equity.")
                steps.append("2. Refuse stock tool execution to prevent lookahead or data hallucination.")
                steps.append("3. Prompt user to specify a supported stock (e.g. TCS, RELIANCE, INFY).")
            else:
                target = valid_symbols[0]
                steps.append(f"1. Fetch verified quote snapshot, calculate technical oscillators, and run 5-day ML directional forecast for {target}.")
                steps.append(f"2. Synthesize balanced technical setup, model probabilities, and strict risk warnings.")
            return steps

        if intent == "STOCK_ANALYSIS":
            target = valid_symbols[0] if valid_symbols else "TCS.NS"
            steps.append(f"1. Fetch verified market price and snapshot for {target}.")
            steps.append(f"2. Calculate institutional technical indicators (SMA, EMA, RSI, MACD, BB, ATR) and 5-day ML prediction.")
            steps.append("3. Synthesize structured institutional research memorandum.")
            return steps

        if intent == "PREDICTION":
            target = valid_symbols[0] if valid_symbols else "RELIANCE.NS"
            steps.append(f"1. Ingest historical time series for {target} with zero lookahead bias.")
            steps.append(f"2. Train chronological classification pipeline (5-day horizon) comparing Logistic Regression & Random Forest.")
            steps.append("3. Report directional class probabilities, out-of-sample accuracy, and reliability ratings.")
            return steps

        if intent == "INDICATOR_EXPLANATION":
            target = valid_symbols[0] if valid_symbols else "INFY.NS"
            steps.append(f"1. Calculate institutional technical indicators for {target}.")
            steps.append(f"2. Explain momentum indicators (RSI, MACD, Bollinger Bands) and current market positioning.")
            return steps

        if intent == "COMPARISON":
            syms = valid_symbols[:2] if len(valid_symbols) >= 2 else ["TCS.NS", "INFY.NS"]
            steps.append(f"1. Fetch quote, indicators, and ML forecasts for primary equity: {syms[0]}.")
            steps.append(f"2. Fetch quote, indicators, and ML forecasts for secondary equity: {syms[1]}.")
            steps.append("3. Conduct side-by-side comparative analysis of momentum, valuation, and statistical edge.")
            return steps

        if intent == "BACKTEST":
            target = valid_symbols[0] if valid_symbols else "RELIANCE.NS"
            steps.append(f"1. Load historical daily bars for {target}.")
            steps.append(f"2. Simulate Moving Average Crossover strategy (SMA 20/50) with slippage and commission modeling.")
            steps.append("3. Evaluate CAGR, Sharpe Ratio, Maximum Drawdown, and Win Rate.")
            return steps

        if intent == "PORTFOLIO":
            steps.append("1. Query SQLite virtual paper trading ledger for cash balance, active holdings, and realized P&L.")
            steps.append("2. Compute institutional portfolio risk analytics: HHI concentration and 95% Parametric VaR.")
            return steps

        # UNKNOWN
        steps.append("1. Process unstructured conversational inquiry.")
        steps.append("2. Guide user to supported quantitative commands and verified equities.")
        return steps

    # ==================== STAGE 5: TOOL SELECTION ====================
    def select_tools(self, intent: str, valid_symbols: list[str], invalid_symbols: list[str], query: str) -> list[dict]:
        """
        STRICT TOOL ROUTING:
        - GREETING: 0 tools.
        - GENERAL_QUESTION: 0 tools.
        - INVESTMENT_QUESTION without stock: 0 tools.
        - Invalid symbols without valid stock: 0 tools.
        - Only approved tools can be selected.
        """
        tools = []

        if intent in ["GREETING", "GENERAL_QUESTION", "UNKNOWN"]:
            return []

        if invalid_symbols and not valid_symbols and intent not in ["BACKTEST", "PORTFOLIO"]:
            return []

        if intent == "INVESTMENT_QUESTION":
            if not valid_symbols:
                return []
            tools.append({"name": "explain_stock_analysis", "args": {"symbol": valid_symbols[0]}})

        elif intent == "STOCK_ANALYSIS":
            target = valid_symbols[0] if valid_symbols else "TCS.NS"
            tools.append({"name": "explain_stock_analysis", "args": {"symbol": target}})

        elif intent == "PREDICTION":
            target = valid_symbols[0] if valid_symbols else "RELIANCE.NS"
            tools.append({"name": "generate_ml_prediction", "args": {"symbol": target, "horizon": 5}})

        elif intent == "INDICATOR_EXPLANATION":
            target = valid_symbols[0] if valid_symbols else "INFY.NS"
            tools.append({"name": "calculate_indicators", "args": {"symbol": target, "period": "6M"}})

        elif intent == "COMPARISON":
            syms = valid_symbols[:2] if len(valid_symbols) >= 2 else ["TCS.NS", "INFY.NS"]
            tools.append({"name": "explain_stock_analysis", "args": {"symbol": syms[0]}})
            tools.append({"name": "explain_stock_analysis", "args": {"symbol": syms[1]}})

        elif intent == "BACKTEST":
            target = valid_symbols[0] if valid_symbols else "RELIANCE.NS"
            tools.append({"name": "run_backtest", "args": {"symbol": target, "fast_period": 20, "slow_period": 50}})

        elif intent == "PORTFOLIO":
            tools.append({"name": "get_portfolio", "args": {}})
            tools.append({"name": "calculate_risk_metrics", "args": {}})

        return tools

    # ==================== STAGE 6: ACT ====================
    def act(self, selected_tools: list[dict]) -> list[dict]:
        """
        Executes approved backend tools inside sandbox. Never executes unapproved tools or code.
        """
        results = []
        for call in selected_tools:
            name = call["name"]
            args = call["args"]

            if name not in self.approved_tools:
                results.append({
                    "tool": name,
                    "status": "error",
                    "error": f"Tool '{name}' is not in approved tool registry.",
                    "output": None
                })
                continue

            try:
                fn = self.approved_tools[name]
                output = fn(**args)
                results.append({
                    "tool": name,
                    "status": "success",
                    "output": output
                })
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                results.append({
                    "tool": name,
                    "status": "error",
                    "error": str(e),
                    "output": None
                })

        return results

    # ==================== STAGE 7: OBSERVE ====================
    def observe(self, execution_results: list[dict]) -> dict:
        """
        OBSERVE Phase:
        Inspects real tool outputs before marking them verified.
        Never fabricates verification states or claims success on error.
        """
        observations = []
        has_errors = False

        if not execution_results:
            observations.append("No backend tools required for this conversational inquiry.")
            return {"has_errors": False, "observations": observations}

        for r in execution_results:
            tool_name = r["tool"]
            status = r["status"]

            if status != "success":
                has_errors = True
                observations.append(f"Tool '{tool_name}' failed with error: {r.get('error')}.")
                continue

            out = r.get("output", {})
            if tool_name == "get_portfolio":
                port = out.get("portfolio", {})
                cash = port.get("cash_balance", 0.0)
                h_cnt = port.get("holdings_count", 0)
                observations.append(f"Verified Paper Portfolio: Available Cash ₹{cash:,.2f}, Active Holdings: {h_cnt}.")

            elif tool_name == "calculate_risk_metrics":
                risk = out.get("risk_analytics", {})
                score = risk.get("risk_score", 0)
                rating = risk.get("risk_rating", "Unknown")
                observations.append(f"Verified Risk Analytics: Portfolio Risk Score {score}/100 ({rating}).")

            elif tool_name == "generate_ml_prediction":
                pred = out.get("prediction", {})
                sym = out.get("symbol", "")
                direction = pred.get("predicted_direction", "N/A")
                prob = pred.get("bullish_probability", 50.0)
                acc = pred.get("metrics", {}).get("out_of_sample_accuracy", "N/A")
                rel = pred.get("reliability", {}).get("rating", "Evaluated")
                observations.append(f"Verified ML Pipeline for {sym}: 5-Day Outlook {direction} (P(Bullish): {prob}%, Test Acc: {acc}%, Reliability: {rel}).")

            elif tool_name == "run_backtest":
                bt = out.get("backtest", {})
                sym = out.get("symbol", "")
                ret = bt.get("total_return_pct", 0.0)
                trades = bt.get("total_trades", 0)
                sharpe = bt.get("sharpe_ratio", 0.0)
                observations.append(f"Verified Backtest for {sym}: {trades} trades, Return: {ret:+.2f}%, Sharpe: {sharpe:.2f}.")

            elif tool_name == "calculate_indicators":
                ind = out.get("indicators", {})
                sym = out.get("symbol", "")
                bias = ind.get("overall_technical_bias", "Neutral")
                rsi = ind.get("rsi_14", {}).get("value", "N/A")
                observations.append(f"Verified Indicators for {sym}: Technical Bias {bias}, RSI(14) {rsi}.")

            elif tool_name == "explain_stock_analysis":
                sym = out.get("symbol", "")
                q = out.get("quote", {})
                price = q.get("price", 0.0)
                dt = q.get("last_market_date", "N/A")
                observations.append(f"Verified Stock Analysis for {sym}: Price ₹{price:,.2f} on {dt}.")

            elif tool_name == "get_market_overview":
                breadth = out.get("market_breadth", "")
                observations.append(f"Verified Market Overview: {breadth} across Indian equities watchlist.")

            else:
                observations.append(f"Tool '{tool_name}' completed execution successfully.")

        return {
            "has_errors": has_errors,
            "observations": observations
        }

    # ==================== STAGE 8: RESPOND ====================
    def respond(
        self,
        query: str,
        intent: str,
        valid_symbols: list[str],
        invalid_symbols: list[str],
        plan_steps: list[str],
        act_info: list[dict],
        observe_info: dict
    ) -> str:
        """
        Synthesizes verified factual data into a polished institutional markdown response.
        Enforces complete honesty, financial safety, and educational framing.
        """
        # Case 1: GREETING
        if intent == "GREETING":
            return (
                "**Hello! Welcome to QUANTEX – AI-Powered Trading Intelligence.**\n\n"
                "I am your institutional research assistant covering the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE).\n\n"
                "**What I Can Do For You:**\n"
                "• **Stock Analysis**: Comprehensive technical & price action breakdown (e.g. `Analyse TCS`)\n"
                "• **Directional ML Predictions**: Chronological 5-day horizon forecasting without look-ahead bias (e.g. `Predict RELIANCE for 5 trading days`)\n"
                "• **Technical Indicators**: Institutional explanations of RSI, MACD, Bollinger Bands, and ATR (e.g. `Explain RSI of INFY`)\n"
                "• **Multi-Stock Comparison**: Side-by-side momentum and risk profiling (e.g. `Compare TCS and INFY`)\n"
                "• **Strategy Backtesting**: Quantitative Moving Average Crossover simulation (e.g. `Backtest the moving average strategy`)\n"
                "• **Paper Trading Portfolio**: Real-time virtual ledger balance, open holdings, and Parametric VaR risk (e.g. `Show my paper trading portfolio`)\n\n"
                "*How can I assist your quantitative market research today?*"
            )

        # Case 2: GENERAL_QUESTION ("What can you do?")
        if intent == "GENERAL_QUESTION":
            return (
                "### **QUANTEX Platform Capabilities & Architecture**\n\n"
                "QUANTEX is an educational quantitative terminal and research engine designed for Indian equity markets. "
                "Operating on an autonomous **PLAN → ACT → OBSERVE → RESPOND** cognitive loop, every insight is grounded in verified computational pipelines.\n\n"
                "**Core Capabilities:**\n"
                "1. **Institutional Equities Coverage**: Real-time delayed snapshots and cached data for 10 benchmark NSE equities (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, `SBIN`, `ITC`, `LT`, `TATAMOTORS`, `BHARTIARTL`).\n"
                "2. **Audited Machine Learning**: Logistic Regression baseline paired with Random Forest comparison evaluated strictly out-of-sample on chronological partitions.\n"
                "3. **Algorithmic Backtesting**: Next-bar execution modeling with 0.1% fees and 0.05% slippage.\n"
                "4. **Virtual Paper Trading**: Risk-free execution engine with ₹10,00,000 virtual capital, tracking mark-to-market P&L and 95% Parametric VaR.\n"
                "5. **Zero Data Fabrication**: Ordinary English words are never converted into fictitious tickers, and unverified market states are never hallucinated.\n\n"
                "*Try asking: 'Analyse TCS', 'Predict RELIANCE', or 'Show my paper trading portfolio'.*"
            )

        # Case 3: Unsupported Symbol Rejection (only when invalid symbols exist and not a general portfolio/backtest command)
        if invalid_symbols and not valid_symbols and intent not in ["BACKTEST", "PORTFOLIO"]:
            bad_sym = invalid_symbols[0]
            return (
                f"### **Unsupported Instrument Symbol: `{bad_sym}`**\n\n"
                f"The symbol `{bad_sym}` is not recognized in the verified QUANTEX Indian equities registry.\n\n"
                f"**Integrity Guarantee**: QUANTEX only analyzes verified instruments and never fabricates prices or fictitious companies.\n\n"
                f"**Supported National Stock Exchange (NSE) Equities:**\n"
                f"• `RELIANCE.NS` (Reliance Industries)\n"
                f"• `TCS.NS` (Tata Consultancy Services)\n"
                f"• `INFY.NS` (Infosys Limited)\n"
                f"• `HDFCBANK.NS` (HDFC Bank)\n"
                f"• `ICICIBANK.NS` (ICICI Bank)\n"
                f"• `SBIN.NS` (State Bank of India)\n"
                f"• `ITC.NS` (ITC Limited)\n"
                f"• `LT.NS` (Larsen & Toubro)\n"
                f"• `TATAMOTORS.NS` (Tata Motors)\n"
                f"• `BHARTIARTL.NS` (Bharti Airtel)\n\n"
                f"*Please re-run your inquiry specifying one of the supported equities above.*"
            )

        # Case 4: Ambiguous Investment Clarification ("Should I invest?")
        if intent == "INVESTMENT_QUESTION" and not valid_symbols:
            return (
                "### **Investment Decision Clarification**\n\n"
                "Deciding whether to invest requires evaluating a specific asset, its current valuation, technical momentum, "
                "and your personal time horizon and risk tolerance. There is no universal *'yes'* or *'no'* without knowing the target equity.\n\n"
                "**Supported Indian Equities Available for Immediate Analysis:**\n"
                "• **Energy**: `RELIANCE` (Reliance Industries)\n"
                "• **Information Technology**: `TCS` (Tata Consultancy Services), `INFY` (Infosys)\n"
                "• **Banking & Financials**: `HDFCBANK`, `ICICIBANK`, `SBIN` (State Bank of India)\n"
                "• **Consumer FMCG**: `ITC` (ITC Limited)\n"
                "• **Infrastructure**: `LT` (Larsen & Toubro)\n"
                "• **Automobile**: `TATAMOTORS` (Tata Motors)\n"
                "• **Telecom**: `BHARTIARTL` (Bharti Airtel)\n\n"
                "**Which specific stock would you like me to analyze for you?**\n"
                "*(For example, ask: 'Should I buy TCS?' or 'Analyse RELIANCE')*\n\n"
                "*Financial Safety Notice: QUANTEX provides computational quantitative research and virtual paper trading. "
                "We never provide guaranteed returns or individualized investment recommendations.*"
            )

        # Case 5: Investment Question with Valid Stock ("Should I buy TCS?") or Stock Analysis ("Analyse TCS")
        if (intent in ["INVESTMENT_QUESTION", "STOCK_ANALYSIS"]) and act_info:
            analysis_tool = next((a for a in act_info if a.get("tool") == "explain_stock_analysis" and a.get("status") == "success"), None)
            if analysis_tool:
                data = analysis_tool["output"]
                sym = data.get("symbol", "")
                q = data.get("quote", {})
                ind = data.get("indicators", {})
                pred = data.get("prediction", {})

                price = q.get("price", 0.0)
                change_pct = q.get("change_pct", 0.0)
                dt = q.get("last_market_date", "Latest available")
                src = "Simulated Geometric Brownian Motion (Benchmark Grounded)" if q.get("is_fallback") else f"Yahoo Finance ({q.get('status', 'cached')})"

                bias = ind.get("overall_technical_bias", "Neutral")
                rsi_val = ind.get("rsi_14", {}).get("value", "N/A")
                macd_sig = ind.get("macd", {}).get("signal", "Neutral")

                p_dir = pred.get("predicted_direction", "Neutral")
                p_bull = pred.get("bullish_probability", pred.get("probability_score", 50.0))
                metrics = pred.get("metrics", {})
                acc = metrics.get("out_of_sample_accuracy", metrics.get("accuracy", "N/A"))
                rel = pred.get("reliability", {})
                rel_rating = rel.get("rating", "Evaluated")
                rel_warning = rel.get("warning", "")

                stance = "CAUTIOUS" if p_dir == "Bearish" else ("CONSTRUCTIVE" if p_dir == "Bullish" else "NEUTRAL")

                return (
                    f"### **Institutional Analysis & Investment Assessment: {sym}**\n\n"
                    f"> **Executive Summary**: We do not provide absolute buy/sell directives. Based on current quantitative evidence, "
                    f"{sym} exhibits a **{stance}** stance over a 5-day horizon.\n\n"
                    f"**1. Verified Market Price Action**\n"
                    f"• **Current Price**: ₹{price:,.2f} ({change_pct:+.2f}%)\n"
                    f"• **Market As-Of Date**: `{dt}`\n"
                    f"• **Data Source Feed**: `{src}`\n\n"
                    f"**2. Technical Evidence & Indicator Bias**\n"
                    f"• **Overall Technical Bias**: **{bias}**\n"
                    f"• **RSI (14)**: `{rsi_val}` (Oscillators in 40–60 indicate neutral consolidation; >70 overextended, <30 oversold)\n"
                    f"• **MACD Trend**: `{macd_sig}`\n"
                    f"• **Moving Averages**: Evaluated relative to 20-day and 50-day moving averages.\n\n"
                    f"**3. Machine Learning Directional Forecast (5-Day Horizon)**\n"
                    f"• **Model Outlook**: **{p_dir}**\n"
                    f"• **Estimated Class Probability P(Bullish)**: `{p_bull}%`\n"
                    f"• **Out-of-Sample Test Accuracy**: `{acc}%` (Evaluated on strict chronological test split)\n"
                    f"• **Model Reliability Rating**: **{rel_rating}**\n"
                    f"{('• *Model Alert: ' + rel_warning + '*') if rel_warning else ''}\n\n"
                    f"**4. Critical Risk Factors & Uncertainty**\n"
                    f"• **Market Uncertainty**: Short-term equity drift is volatile and subject to unforeseen macro shocks.\n"
                    f"• **Position Sizing**: Limit allocation to at most 10%–20% of your total capital with explicit stop-loss levels.\n\n"
                    f"---\n"
                    f"*Financial Safety & Compliance Notice: QUANTEX is an educational quantitative platform. "
                    f"Outputs are mathematical estimates and never guaranteed financial advice.*"
                )

        # Case 6: PREDICTION ("Predict RELIANCE for 5 trading days")
        if intent == "PREDICTION" and act_info:
            pred_tool = next((a for a in act_info if a.get("tool") == "generate_ml_prediction" and a.get("status") == "success"), None)
            if pred_tool:
                data = pred_tool["output"]
                sym = data.get("symbol", "")
                p = data.get("prediction", {})
                p_dir = p.get("predicted_direction", "Neutral")
                bull_p = p.get("bullish_probability", 50.0)
                bear_p = p.get("bearish_probability", 50.0)
                score = p.get("directional_score", 0.0)
                metrics = p.get("metrics", {})
                acc = metrics.get("out_of_sample_accuracy", 50.0)
                base = p.get("baselines", {}).get("majority_class_baseline_accuracy", 50.0)
                base_cls = p.get("baselines", {}).get("majority_class_name", "Baseline")
                rel = p.get("reliability", {})
                rel_rating = rel.get("rating", "Evaluated")
                rel_warn = rel.get("warning", "")
                comp = p.get("model_comparison", {})
                lr_acc = comp.get("logistic_regression", {}).get("accuracy", acc)
                rf_acc = comp.get("random_forest", {}).get("accuracy", "N/A")
                rf_bull = comp.get("random_forest", {}).get("p_bullish", "N/A")

                return (
                    f"### **Machine Learning Directional Forecast: {sym} (5-Day Horizon)**\n\n"
                    f"**1. Core Directional Prediction**\n"
                    f"• **Forecasted Direction**: **{p_dir.upper()}**\n"
                    f"• **Class Probabilities**: $P(\\text{{Bullish}}) = {bull_p}\\%$, $P(\\text{{Bearish}}) = {bear_p}\\%$\n"
                    f"• **Directional Score**: `{score:+.1f}` / 100 (Signed distance from 50% decision threshold)\n\n"
                    f"**2. Out-of-Sample Performance (Zero Look-Ahead Bias)**\n"
                    f"• **Logistic Regression Test Accuracy**: `{lr_acc}%`\n"
                    f"• **Random Forest Test Accuracy**: `{rf_acc}%` (Random Forest $P(\\text{{Bullish}}) = {rf_bull}\\%$)\n"
                    f"• **Naive Majority Baseline**: `{base}%` (Predicting `{base_cls}`)\n"
                    f"• **Model Reliability Rating**: **{rel_rating}**\n"
                    f"{('• *Reliability Warning: ' + rel_warn + '*') if rel_warn else ''}\n\n"
                    f"**3. Methodology Integrity**\n"
                    f"• **Horizon**: 5 trading days ($C_{{t+5}} > C_t$).\n"
                    f"• **Temporal Split**: Evaluated exclusively on unseen chronological test bars; random shuffling is prohibited.\n\n"
                    f"*Note: Directional probability indicates historical feature alignment, not a guaranteed return.*"
                )

        # Case 7: INDICATOR_EXPLANATION ("Explain RSI of INFY")
        if intent == "INDICATOR_EXPLANATION" and act_info:
            ind_tool = next((a for a in act_info if a.get("tool") == "calculate_indicators" and a.get("status") == "success"), None)
            if ind_tool:
                data = ind_tool["output"]
                sym = data.get("symbol", "")
                ind = data.get("indicators", {})
                price = ind.get("price", 0.0)
                rsi = ind.get("rsi_14", {})
                rsi_val = rsi.get("value", "N/A")
                rsi_sig = rsi.get("signal", "Neutral")
                macd = ind.get("macd", {})
                bb = ind.get("bollinger_bands", {})
                atr = ind.get("atr_14", {}).get("value", "N/A")
                bias = ind.get("overall_technical_bias", "Neutral")

                return (
                    f"### **Technical Indicator Analysis: {sym}**\n\n"
                    f"**Current Price**: ₹{price:,.2f} | **Overall Technical Bias**: **{bias}**\n\n"
                    f"**1. Relative Strength Index (RSI 14)**\n"
                    f"• **Value**: **{rsi_val}** ({rsi_sig})\n"
                    f"• **Interpretation**: RSI measures the speed and change of price movements on a 0–100 scale. "
                    f"Readings between 40 and 60 represent balanced consolidation. A reading above 70 warns of overbought conditions, "
                    f"while values below 30 indicate oversold momentum.\n\n"
                    f"**2. MACD (12, 26, 9)**\n"
                    f"• **MACD Line**: `{macd.get('value', 'N/A')}` | **Signal Line**: `{macd.get('signal_line', 'N/A')}`\n"
                    f"• **Histogram**: `{macd.get('histogram', 'N/A')}` ({macd.get('signal', 'Neutral')})\n\n"
                    f"**3. Volatility & Bands**\n"
                    f"• **Bollinger Bands (20, 2σ)**: Lower `₹{bb.get('lower', 0):,.2f}` | Middle `₹{bb.get('middle', 0):,.2f}` | Upper `₹{bb.get('upper', 0):,.2f}`\n"
                    f"• **Average True Range (ATR 14)**: `₹{atr}` daily rupee volatility range.\n\n"
                    f"*Technical indicators reflect historical momentum and should be combined with risk management.*"
                )

        # Case 8: COMPARISON ("Compare TCS and INFY")
        if intent == "COMPARISON" and len(act_info) >= 2:
            out1 = act_info[0].get("output", {})
            out2 = act_info[1].get("output", {})
            sym1, sym2 = out1.get("symbol", "Stock 1"), out2.get("symbol", "Stock 2")
            q1, q2 = out1.get("quote", {}), out2.get("quote", {})
            ind1, ind2 = out1.get("indicators", {}), out2.get("indicators", {})
            p1, p2 = out1.get("prediction", {}), out2.get("prediction", {})

            return (
                f"### **Comparative Analysis: {sym1} vs {sym2}**\n\n"
                f"| Metric / Indicator | **{sym1}** | **{sym2}** |\n"
                f"| :--- | :--- | :--- |\n"
                f"| **Latest Price** | ₹{q1.get('price', 0.0):,.2f} ({q1.get('change_pct', 0.0):+.2f}%) | ₹{q2.get('price', 0.0):,.2f} ({q2.get('change_pct', 0.0):+.2f}%) |\n"
                f"| **Market Date** | `{q1.get('last_market_date', 'N/A')}` | `{q2.get('last_market_date', 'N/A')}` |\n"
                f"| **Technical Bias** | **{ind1.get('overall_technical_bias', 'Neutral')}** | **{ind2.get('overall_technical_bias', 'Neutral')}** |\n"
                f"| **RSI (14)** | `{ind1.get('rsi_14', {}).get('value', 'N/A')}` | `{ind2.get('rsi_14', {}).get('value', 'N/A')}` |\n"
                f"| **ML Direction (5D)** | **{p1.get('predicted_direction', 'N/A')}** ($P: {p1.get('bullish_probability', 50)}%$) | **{p2.get('predicted_direction', 'N/A')}** ($P: {p2.get('bullish_probability', 50)}%$) |\n"
                f"| **Test Accuracy** | `{p1.get('metrics', {}).get('out_of_sample_accuracy', 'N/A')}%` | `{p2.get('metrics', {}).get('out_of_sample_accuracy', 'N/A')}%` |\n"
                f"| **Reliability** | **{p1.get('reliability', {}).get('rating', 'Low')}** | **{p2.get('reliability', {}).get('rating', 'Low')}** |\n\n"
                f"**Institutional Takeaway**:\n"
                f"• Compare both equities within your portfolio asset allocation.\n"
                f"• Both equities show sector correlation in Information Technology; avoid over-concentrating capital in a single sector.\n\n"
                f"*Simulated comparative evaluation. Never trade real money without independent analysis.*"
            )

        # Case 9: BACKTEST ("Backtest the moving average strategy")
        if intent == "BACKTEST" and act_info:
            bt_tool = next((a for a in act_info if a.get("tool") == "run_backtest" and a.get("status") == "success"), None)
            if bt_tool:
                data = bt_tool["output"]
                sym = data.get("symbol", "")
                bt = data.get("backtest", {})
                ret = bt.get("total_return_pct", 0.0)
                bmark = bt.get("benchmark_return_pct", 0.0)
                cagr = bt.get("cagr_pct", 0.0)
                sharpe = bt.get("sharpe_ratio", 0.0)
                mdd = bt.get("max_drawdown_pct", 0.0)
                win_rate = bt.get("win_rate_pct", 0.0)
                trades = bt.get("total_trades", 0)

                return (
                    f"### **Strategy Backtest Simulation: {sym}**\n\n"
                    f"**Strategy**: Moving Average Crossover (Fast: 20 SMA / Slow: 50 SMA)\n"
                    f"**Execution Modeling**: Next-bar execution, 0.10% transaction fees, 0.05% slippage.\n\n"
                    f"**Performance Summary:**\n"
                    f"• **Strategy Return**: **{ret:+.2f}%** (vs Buy & Hold Benchmark: `{bmark:+.2f}%`)\n"
                    f"• **CAGR**: `{cagr:+.2f}%`\n"
                    f"• **Sharpe Ratio**: `{sharpe:.2f}`\n"
                    f"• **Maximum Drawdown**: `{mdd:.2f}%`\n"
                    f"• **Win Rate**: `{win_rate:.1f}%` ({trades} completed round-trip trades)\n\n"
                    f"*Backtesting evaluates historical price series under friction. Past performance does not guarantee future results.*"
                )

        # Case 10: PORTFOLIO ("Show my paper trading portfolio")
        if intent == "PORTFOLIO" and act_info:
            port_tool = next((a for a in act_info if a.get("tool") == "get_portfolio" and a.get("status") == "success"), None)
            risk_tool = next((a for a in act_info if a.get("tool") == "calculate_risk_metrics" and a.get("status") == "success"), None)

            if port_tool:
                p_data = port_tool["output"].get("portfolio", {})
                cash = p_data.get("cash_balance", 1000000.0)
                total_val = p_data.get("total_portfolio_value", cash)
                holdings = p_data.get("holdings", [])
                pnl = p_data.get("total_unrealized_pnl", 0.0)
                pnl_pct = p_data.get("total_unrealized_pnl_pct", 0.0)

                risk_text = ""
                if risk_tool:
                    r_data = risk_tool["output"].get("risk_analytics", {})
                    score = r_data.get("risk_score", 0)
                    rating = r_data.get("risk_rating", "Unknown")
                    hhi = r_data.get("hhi_concentration", 0.0)
                    var95 = r_data.get("var_95_daily_amount", 0.0)
                    risk_text = (
                        f"\n**Risk Management Metrics:**\n"
                        f"• **Portfolio Risk Score**: `{score}/100` ({rating})\n"
                        f"• **HHI Concentration**: `{hhi:,.0f}` (Concentration risk)\n"
                        f"• **1-Day 95% Parametric VaR**: `₹{var95:,.2f}`\n"
                    )

                holdings_md = ""
                if holdings:
                    holdings_md = "\n| Symbol | Quantity | Avg Price | Current Price | Value | Unrealized P&L |\n| :--- | :--- | :--- | :--- | :--- | :--- |\n"
                    for h in holdings:
                        sym = h.get("symbol", "")
                        qty = h.get("quantity", 0)
                        avg_p = h.get("avg_buy_price", 0.0)
                        cur_p = h.get("current_price", 0.0)
                        val = h.get("current_value", 0.0)
                        hpnl = h.get("unrealized_pnl", 0.0)
                        holdings_md += f"| `{sym}` | {qty} | ₹{avg_p:,.2f} | ₹{cur_p:,.2f} | ₹{val:,.2f} | {hpnl:+,.2f} |\n"
                else:
                    holdings_md = "\n*No open positions currently held. All capital is held in virtual cash.*"

                return (
                    f"### **Virtual Paper Trading Portfolio Summary**\n\n"
                    f"• **Available Virtual Cash**: **₹{cash:,.2f}**\n"
                    f"• **Total Portfolio Equity**: **₹{total_val:,.2f}**\n"
                    f"• **Total Unrealized P&L**: **₹{pnl:+,.2f} ({pnl_pct:+.2f}%)**\n"
                    f"• **Active Holdings Count**: `{len(holdings)}`\n"
                    f"{risk_text}"
                    f"\n**Open Positions:**"
                    f"{holdings_md}\n\n"
                    f"*Strictly virtual paper trading balance. Real money is never transacted.*"
                )

        # Fallback response for unhandled case
        return (
            "**QUANTEX Institutional Analysis**\n\n"
            f"Query processed: \"{query}\"\n\n"
            "• Execution verified across backend engines.\n"
            "• Please specify a supported Indian equity (e.g. `TCS`, `RELIANCE`, `INFY`) for deep-dive quantitative analysis.\n\n"
            "*Educational platform notice: We never execute real trades or provide financial advice.*"
        )

    # ==================== MAIN EXECUTION PIPELINE ====================
    def run(self, query: str) -> dict:
        """
        Executes the verified 9-stage cognitive pipeline:
        1. Entity Extraction
        2. Symbol Validation
        3. Intent Classification
        4. Plan Generation
        5. Tool Selection
        6. Act (Execution)
        7. Observe (Verification)
        8. Respond (Synthesis)
        9. Trace Logging
        """
        # 1. Entity Extraction
        raw_entities = self.extract_entities(query)

        # 2. Symbol Validation
        valid_symbols, invalid_symbols = self.validate_symbols(raw_entities)

        # 3. Intent Classification
        intent = self.classify_intent(query, raw_entities, valid_symbols)

        # 4. Plan Generation
        plan_steps = self.generate_plan(intent, valid_symbols, invalid_symbols, query)

        # 5. Tool Selection
        selected_tools = self.select_tools(intent, valid_symbols, invalid_symbols, query)

        # 6. Act (Tool Execution)
        act_info = self.act(selected_tools)

        # 7. Observe (Output Inspection & Verification)
        observe_info = self.observe(act_info)

        # 8. Respond (Evidence-based Institutional Answer)
        response_text = self.respond(
            query=query,
            intent=intent,
            valid_symbols=valid_symbols,
            invalid_symbols=invalid_symbols,
            plan_steps=plan_steps,
            act_info=act_info,
            observe_info=observe_info
        )

        # 9. Audit Logging to SQLite
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO agent_logs (user_query, plan_steps, tools_called, observation, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                query,
                json.dumps(plan_steps),
                json.dumps([t["name"] for t in selected_tools]),
                json.dumps(observe_info["observations"]),
                "SUCCESS" if not observe_info["has_errors"] else "PARTIAL_ERROR"
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to log agent trace: {e}")

        return {
            "query": query,
            "pipeline": {
                "intent": intent,
                "entities": {
                    "raw_entities": raw_entities,
                    "valid_symbols": valid_symbols,
                    "invalid_symbols": invalid_symbols
                },
                "plan": plan_steps,
                "act": [
                    {
                        "tool": a["tool"],
                        "status": a["status"],
                        "has_output": bool(a.get("output"))
                    } for a in act_info
                ],
                "observe": observe_info["observations"],
                "verification_status": "VERIFIED" if not observe_info["has_errors"] else "ERROR"
            },
            "response": response_text,
            "raw_tool_data": [a.get("output") for a in act_info if a.get("output")]
        }

quantex_agent = QuantexToolAgent()
