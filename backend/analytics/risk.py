"""
Institutional Risk Management and Analytics Engine.
Calculates portfolio exposure, position concentration (HHI), historical volatility,
parametric Value-at-Risk (95% VaR), and stop-loss impact stress tests.
"""
import numpy as np
import pandas as pd
from backend.trading.paper_trading import paper_trading_engine
from backend.market_data.yahoo_provider import market_data_provider

def calculate_portfolio_risk() -> dict:
    """
    Computes institutional risk metrics for the active paper trading portfolio:
    1. Total Equity Exposure & Cash Reserve Ratio
    2. Concentration Analysis (Herfindahl-Hirschman Index and Top Holdings)
    3. Portfolio Weighted Volatility
    4. 1-Day 95% Parametric Value at Risk (VaR)
    5. Stress-Test Scenarios (-2%, -5%, -10% market drawdowns)
    6. Actionable Risk Alerts and Warning Flags
    """
    portfolio = paper_trading_engine.get_portfolio()
    total_val = portfolio["total_portfolio_value"]
    cash = portfolio["cash_balance"]
    holdings = portfolio["holdings"]

    if not holdings or total_val <= 0:
        return {
            "status": "empty_portfolio",
            "portfolio_value": total_val,
            "cash_balance": cash,
            "equity_exposure_pct": 0.0,
            "cash_pct": 100.0,
            "hhi_concentration": 0,
            "concentration_level": "Low (100% Cash)",
            "estimated_daily_volatility_pct": 0.0,
            "var_95_daily_amount": 0.0,
            "stress_tests": {
                "market_down_2pct": {"loss_amount": 0.0, "projected_value": total_val},
                "market_down_5pct": {"loss_amount": 0.0, "projected_value": total_val},
                "market_down_10pct": {"loss_amount": 0.0, "projected_value": total_val}
            },
            "risk_score": 10,  # 0-100 scale
            "risk_rating": "Ultra Conservative (Liquid Cash)",
            "warnings": ["Portfolio currently holds 100% cash. No active equity market exposure."]
        }

    # 1. Exposure
    holdings_val = portfolio["holdings_value"]
    equity_exposure_pct = round((holdings_val / total_val) * 100, 2)
    cash_pct = round((cash / total_val) * 100, 2)

    # 2. Position Concentration (HHI Index)
    # HHI = Sum of (Weight %)^2. Range: near 0 to 10,000.
    hhi = 0.0
    weights = []
    symbol_volatilities = []
    
    warnings = []
    for h in holdings:
        w = (h["current_value"] / total_val) * 100.0
        hhi += (w ** 2)
        weights.append(w / 100.0)

        # Retrieve volatility
        try:
            df, _ = market_data_provider.get_historical_data(h["symbol"], period="3M")
            close = df["Close"].astype(float)
            log_ret = np.log(close / close.shift(1)).dropna()
            daily_std = float(log_ret.std())
            symbol_volatilities.append(daily_std if not np.isnan(daily_std) else 0.015)
        except Exception:
            symbol_volatilities.append(0.015)

        # Single position warning (> 35%)
        if w > 35.0:
            warnings.append(f"High concentration warning: {h['symbol']} represents {w:.1f}% of total portfolio value.")

    hhi = round(hhi, 1)
    if hhi > 3000:
        concentration_level = "High Concentration Risk"
    elif hhi > 1800:
        concentration_level = "Moderate Concentration"
    else:
        concentration_level = "Well Diversified"

    # 3. Portfolio Volatility (Weighted Average daily volatility)
    weighted_daily_vol = float(np.sum(np.array(weights) * np.array(symbol_volatilities)))
    annualized_vol_pct = round(weighted_daily_vol * np.sqrt(252) * 100, 2)

    # 4. Parametric Value at Risk (1-day 95% confidence -> Z = 1.645)
    # 95% VaR = Portfolio Value * Equity Exposure * 1.645 * daily_vol
    var_95_amount = round(holdings_val * 1.645 * weighted_daily_vol, 2)

    # 5. Stress Test Scenarios on Equity Holdings
    stress_tests = {
        "market_down_2pct": {
            "loss_amount": round(holdings_val * 0.02, 2),
            "projected_value": round(total_val - (holdings_val * 0.02), 2)
        },
        "market_down_5pct": {
            "loss_amount": round(holdings_val * 0.05, 2),
            "projected_value": round(total_val - (holdings_val * 0.05), 2)
        },
        "market_down_10pct": {
            "loss_amount": round(holdings_val * 0.10, 2),
            "projected_value": round(total_val - (holdings_val * 0.10), 2)
        }
    }

    # 6. Overall Risk Score (0 - 100)
    # Factors: Equity exposure (0-40 pts), Concentration HHI (0-30 pts), Volatility (0-30 pts)
    exposure_pts = min(40, (equity_exposure_pct / 100.0) * 40)
    conc_pts = min(30, (hhi / 4000.0) * 30)
    vol_pts = min(30, (annualized_vol_pct / 30.0) * 30)
    risk_score = int(round(exposure_pts + conc_pts + vol_pts))

    if risk_score > 70:
        risk_rating = "High Risk"
    elif risk_score > 40:
        risk_rating = "Moderate Risk"
    else:
        risk_rating = "Low / Conservative Risk"

    if equity_exposure_pct > 85.0:
        warnings.append("Low cash buffer: Equity exposure exceeds 85%. Consider maintaining liquidity for drawdowns.")

    return {
        "status": "success",
        "portfolio_value": round(total_val, 2),
        "holdings_value": round(holdings_val, 2),
        "cash_balance": round(cash, 2),
        "equity_exposure_pct": equity_exposure_pct,
        "cash_pct": cash_pct,
        "hhi_concentration": hhi,
        "concentration_level": concentration_level,
        "annualized_volatility_pct": annualized_vol_pct,
        "var_95_daily_amount": var_95_amount,
        "stress_tests": stress_tests,
        "risk_score": risk_score,
        "risk_rating": risk_rating,
        "warnings": warnings
    }
