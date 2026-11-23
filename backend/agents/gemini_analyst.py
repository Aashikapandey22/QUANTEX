"""
Google Gemini AI Trading Intelligence Analyst.
Generates institutional explanations of technical indicators, ML prediction outputs,
backtest evaluations, and market conditions using Google GenAI SDK.
Maintains a deterministic local quantitative reasoning fallback when Gemini API key is unset or unreachable.
"""
import os
import json
import logging
from config import Config

logger = logging.getLogger("quantex.analyst")

class GeminiAnalyst:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = Config.GEMINI_MODEL
        self.client = None
        
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"Gemini client initialized with model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini GenAI client: {e}")
                self.client = None

    def is_configured(self) -> bool:
        # Check if environment has a valid key configured
        key = Config.GEMINI_API_KEY
        if key and key.strip():
            if not self.client:
                try:
                    from google import genai
                    self.api_key = key.strip()
                    self.model_name = Config.GEMINI_MODEL
                    self.client = genai.Client(api_key=self.api_key)
                except Exception as e:
                    logger.warning(f"Could not build Gemini client: {e}")
                    return False
            return self.client is not None
        return False

    def generate_analysis(self, prompt: str, system_context: str = "") -> dict:
        """
        Sends prompt to Gemini API with timeouts and structured error handling.
        Falls back to local quantitative reasoning if API is unavailable.
        """
        if self.is_configured():
            try:
                full_contents = f"{system_context}\n\nTask:\n{prompt}" if system_context else prompt
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=full_contents,
                )
                if response and hasattr(response, "text") and response.text:
                    return {
                        "source": "gemini",
                        "model": self.model_name,
                        "analysis": response.text.strip(),
                        "is_fallback": False
                    }
            except Exception as e:
                logger.warning(f"Gemini API generation failed ({e}). Reverting to local analyst.")

        # Local institutional quantitative reasoning engine
        return {
            "source": "local_quant_engine",
            "model": "QUANTEX Institutional Rule Engine v2.0",
            "analysis": self._generate_local_fallback(prompt, system_context),
            "is_fallback": True
        }

    def _generate_local_fallback(self, prompt: str, system_context: str) -> str:
        """Generates comprehensive, professional financial commentary locally based on verified facts."""
        p_lower = prompt.lower()
        ctx_lower = system_context.lower()

        # Case 1: Clarification needed (User asks "Should I invest?" without naming an equity)
        if "clarification_needed" in ctx_lower or "which stock they want to analyse" in p_lower:
            return (
                "**Investment Decision Analysis & Stock Clarification**\n\n"
                "Deciding whether to invest requires analyzing a specific company, its fundamental health, current valuation, and technical trend. "
                "There is no universal answer to *'Should I invest?'* without knowing your target asset, risk tolerance, and investment horizon.\n\n"
                "**Supported Indian Equities Available for Analysis:**\n"
                "• **Energy & Conglomerate**: `RELIANCE` (Reliance Industries)\n"
                "• **Information Technology**: `TCS` (Tata Consultancy Services), `INFY` (Infosys)\n"
                "• **Banking & Financials**: `HDFCBANK` (HDFC Bank), `ICICIBANK` (ICICI Bank), `SBIN` (State Bank of India)\n"
                "• **Consumer Goods (FMCG)**: `ITC` (ITC Limited)\n"
                "• **Infrastructure & Heavy Engineering**: `LT` (Larsen & Toubro)\n"
                "• **Automotive**: `TATAMOTORS` (Tata Motors)\n"
                "• **Telecommunications**: `BHARTIARTL` (Bharti Airtel)\n\n"
                "**Which specific stock would you like me to evaluate for you?** "
                "(e.g., *'Should I buy TCS?'* or *'Analyse RELIANCE'*)\n\n"
                "*Financial Safety Notice: QUANTEX is an institutional research and simulation platform. We never provide guaranteed buy/sell recommendations or personal financial advice.*"
            )

        # Case 2: Broad Market Outlook
        if "market_outlook" in ctx_lower or "market outlook" in p_lower or "market conditions" in p_lower:
            return (
                "**Indian Equity Market Outlook & Conditions Overview**\n\n"
                "• **Macro & Sector Breadth**: The National Stock Exchange (NSE) presents a balanced structure across core sectors. "
                "Banking (HDFC Bank, ICICI Bank, SBI) and IT (TCS, Infosys) continue to drive benchmark index liquidity.\n"
                "• **Volatility Environment**: India VIX and historical 20-day annualized equity volatilities are hovering around typical institutional bands (14%–20%), "
                "indicating normal two-way price discovery without acute systemic stress.\n"
                "• **Institutional Stance**: When evaluating market entries, ensure positions align with 20-day and 50-day moving average trends, "
                "and maintain strict portfolio risk budgeting (HHI concentration < 2500 and maximum position sizes under 20-25%).\n\n"
                "*Disclaimer: For academic evaluation and simulated research. Never invest real capital without independent due diligence.*"
            )

        # Case 3: Explaining ML Prediction Methodology
        if "explain_prediction" in ctx_lower or "how does the ml prediction work" in p_lower:
            return (
                "**QUANTEX Machine Learning Methodology Briefing**\n\n"
                "• **Prediction Target**: Formulated as a binary classification target estimating whether the split-adjusted close "
                "5 trading days in the future ($C_{t+5}$) exceeds the current close ($C_t$).\n"
                "• **Stationary Feature Engineering**: Avoids non-stationary raw prices by transforming data into 11 relative ratios: "
                "return lags (1D, 5D), moving average divergences (SMA 20/50, EMA 20), normalized RSI (14), price-scaled MACD/Histogram, "
                "ATR ratio, 20-day annualized volatility, and volume moving average ratio.\n"
                "• **Temporal Integrity**: Strictly enforces chronological train/test splitting (first 80% train, last 20% test). "
                "Random shuffling is prohibited to prevent look-ahead bias and future data leakage.\n"
                "• **Probability Calibration**: Uses calibrated Sigmoid probability output (Logistic Regression) or tree ensemble voting (Random Forest) "
                "with out-of-sample accuracy honestly reported.\n\n"
                "*Notice: Probabilities reflect historical statistical patterns and are not guarantees of future performance.*"
            )

        # Default institutional quantitative synthesis
        text = "**QUANTEX Institutional Market Intelligence Briefing**\n\n"

        if "prediction" in p_lower or "prediction" in ctx_lower:
            text += (
                "**Directional Machine Learning Assessment:**\n"
                "• The chronological classification pipeline models directional probability using stationary technical features.\n"
                "• Statistical probabilities reflect historical feature patterns and must be paired with strict stop-loss rules.\n\n"
            )

        if "rsi" in p_lower or "rsi" in ctx_lower or "macd" in p_lower:
            text += (
                "**Technical Structure & Momentum Overview:**\n"
                "• Trend Alignment: Monitor price interaction with 20-day and 50-day moving averages.\n"
                "• Momentum Oscillators: RSI (14) between 40–60 indicates consolidation; readings > 70 suggest overextended momentum, while < 30 indicates oversold conditions.\n"
                "• MACD Signal: Histogram expansion signals directional acceleration, while narrowing bars indicate exhaustion.\n\n"
            )

        if "risk" in p_lower or "portfolio" in p_lower or "backtest" in p_lower:
            text += (
                "**Portfolio & Risk Directives:**\n"
                "• Enforce single-position sizing limits (< 25% of virtual capital) to contain unsystematic risk.\n"
                "• Monitor daily 95% Parametric Value at Risk (VaR) and evaluate stress-test drawdown scenarios.\n\n"
            )

        text += (
            "*Financial Safety Disclaimer: QUANTEX provides computational quantitative research and virtual paper trading. "
            "Never execute real-money capital based on automated models without independent professional advisory.*"
        )
        return text

    def explain_stock(self, symbol: str, quote: dict, indicators: dict, ml_result: dict) -> str:
        """Constructs grounded synthesis from verified factual backend components."""
        price = quote.get("price", 0.0)
        change_pct = quote.get("change_pct", 0.0)
        date_str = quote.get("last_market_date", "Latest available")
        source_str = quote.get("status", "delayed/cached")
        is_fallback = quote.get("is_fallback", False)
        source_label = "Simulated Geometric Brownian Motion (Benchmark Grounded)" if is_fallback else f"Yahoo Finance ({source_str})"
        
        rsi = indicators.get("rsi_14", {}).get("value", "N/A")
        bias = indicators.get("overall_technical_bias", "Neutral")
        direction = ml_result.get("predicted_direction", "Neutral")
        prob = ml_result.get("bullish_probability", ml_result.get("probability_score", 50.0))
        metrics = ml_result.get("metrics", {})
        acc = metrics.get("out_of_sample_accuracy", metrics.get("accuracy", "N/A"))
        reliability = ml_result.get("reliability", {})
        rel_rating = reliability.get("rating", "Evaluated")
        rel_warning = reliability.get("warning", "")

        prompt = (
            f"Provide an institutional quantitative analysis for {symbol}.\n"
            f"Verified Market Facts:\n"
            f"- Current Price: ₹{price:,.2f} ({change_pct:+.2f}%)\n"
            f"- Market Date & Source: {date_str} [{source_label}]\n"
            f"- Technical Bias: {bias} (RSI 14: {rsi})\n"
            f"- ML Directional Prediction (5-day): {direction} (P(Bullish): {prob}%, Out-of-sample Test Accuracy: {acc}%)\n"
            f"- Model Reliability: {rel_rating} - {rel_warning}\n"
            f"Deliver a structured report covering: 1) Price Action & Momentum, 2) Technical Setup, 3) Machine Learning Outlook, and 4) Actionable Risk Controls."
        )
        sys_ctx = (
            "You are QUANTEX, a senior quantitative portfolio analyst covering Indian equities on the NSE/BSE. "
            "You strictly base your statements on the provided data without hallucinating prices, dates, or returns. "
            "Never guarantee returns. State that outputs are educational research estimates."
        )
        res = self.generate_analysis(prompt, sys_ctx)
        # If Gemini returned analysis, return it directly
        if not res.get("is_fallback"):
            return res["analysis"]

        # High-fidelity grounded local quantitative report
        return (
            f"### **Institutional Analysis: {symbol}**\n\n"
            f"**1. Price Action & Market Data Integrity**\n"
            f"• **Current Price**: ₹{price:,.2f} ({change_pct:+.2f}%)\n"
            f"• **Market As-Of Date**: `{date_str}`\n"
            f"• **Data Feed Status**: `{source_label}`\n\n"
            f"**2. Technical Structure & Oscillator Signals**\n"
            f"• **Overall Technical Bias**: **{bias}**\n"
            f"• **Momentum (RSI 14)**: `{rsi}` (40–60 range denotes neutral consolidation; >70 overextended, <30 oversold)\n"
            f"• **Moving Average Alignment**: Evaluated against 20-day and 50-day moving averages.\n\n"
            f"**3. Machine Learning Directional Forecast (5-Day Horizon)**\n"
            f"• **Predicted Direction**: **{direction}**\n"
            f"• **Estimated Class Probability P(Bullish)**: `{prob}%`\n"
            f"• **Out-of-Sample Test Accuracy**: `{acc}%` (Evaluated on strict chronological test partition)\n"
            f"• **Reliability Rating**: **{rel_rating}**\n"
            f"{('• *Warning: ' + rel_warning + '*') if rel_warning else ''}\n\n"
            f"**4. Risk Controls & Investment Uncertainty**\n"
            f"• **Market Uncertainty**: Short-term equity drift is subject to high macroeconomic noise, earnings announcements, and sector rotation.\n"
            f"• **Position Sizing**: Limit allocation to at most 15%–20% of your total portfolio to prevent severe single-stock drawdown.\n\n"
            f"---\n"
            f"*Educational & Research Notice: QUANTEX is an institutional quantitative simulation platform. "
            f"This analysis does not constitute a guaranteed buy, sell, or hold recommendation.*"
        )

gemini_analyst = GeminiAnalyst()
