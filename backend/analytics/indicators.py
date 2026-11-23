"""
Quantitative Technical Indicators Engine.
Calculates mathematical indicators on OHLCV data using Pandas & NumPy.
Includes explanation metadata and signal interpretation.
"""
import numpy as np
import pandas as pd

def calculate_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Computes standard institutional technical indicators on an OHLCV dataframe:
    - SMA 20, SMA 50
    - EMA 20
    - RSI 14 (Wilder's RSI)
    - MACD (12, 26), MACD Signal (9), MACD Histogram
    - Bollinger Bands (20, 2-std)
    - ATR 14 (Average True Range)
    - Daily Returns
    - Historical Volatility (20-day rolling annualized)
    - Volume SMA 20
    """
    if df.empty or len(df) < 5:
        return df

    out = df.copy()

    # Ensure Close is float
    close = out["Close"].astype(float)
    high = out["High"].astype(float)
    low = out["Low"].astype(float)
    volume = out["Volume"].astype(float)

    # 1. Moving Averages
    out["SMA_20"] = close.rolling(window=20, min_periods=1).mean().round(2)
    out["SMA_50"] = close.rolling(window=50, min_periods=1).mean().round(2)
    out["EMA_20"] = close.ewm(span=20, adjust=False).mean().round(2)

    # 2. RSI (14-period Wilder's smoothing)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    # Exponential moving average for RSI smoothing
    avg_gain = gain.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    out["RSI_14"] = rsi.fillna(50.0).round(2)

    # 3. MACD (12, 26, 9)
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_line = ema_12 - ema_26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    macd_hist = macd_line - signal_line

    out["MACD"] = macd_line.round(2)
    out["MACD_Signal"] = signal_line.round(2)
    out["MACD_Hist"] = macd_hist.round(2)

    # 4. Bollinger Bands (20-period, 2-std)
    rolling_mean_20 = close.rolling(window=20, min_periods=1).mean()
    rolling_std_20 = close.rolling(window=20, min_periods=1).std().fillna(0)
    out["BB_Upper"] = (rolling_mean_20 + 2 * rolling_std_20).round(2)
    out["BB_Middle"] = rolling_mean_20.round(2)
    out["BB_Lower"] = (rolling_mean_20 - 2 * rolling_std_20).round(2)

    # 5. Average True Range (ATR 14)
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    out["ATR_14"] = true_range.ewm(alpha=1/14, min_periods=14, adjust=False).mean().fillna(true_range.mean()).round(2)

    # 6. Returns & Volatility
    out["Daily_Return"] = (close.pct_change() * 100).fillna(0.0).round(2)
    # Annualized 20-day rolling volatility
    log_returns = np.log(close / close.shift(1))
    rolling_vol = (log_returns.rolling(window=20, min_periods=5).std() * np.sqrt(252) * 100).fillna(18.0)
    out["Historical_Volatility"] = rolling_vol.round(2)

    # 7. Volume SMA 20
    out["Volume_SMA_20"] = volume.rolling(window=20, min_periods=1).mean().round(0)

    return out

def get_latest_indicators_summary(df_with_indicators: pd.DataFrame) -> dict:
    """
    Extracts the latest indicator values along with quantitative signals and plain-English explanations.
    """
    if df_with_indicators.empty:
        return {}

    latest = df_with_indicators.iloc[-1]
    close = float(latest["Close"])
    rsi = float(latest.get("RSI_14", 50))
    macd = float(latest.get("MACD", 0))
    macd_sig = float(latest.get("MACD_Signal", 0))
    macd_hist = float(latest.get("MACD_Hist", 0))
    sma_20 = float(latest.get("SMA_20", close))
    sma_50 = float(latest.get("SMA_50", close))
    ema_20 = float(latest.get("EMA_20", close))
    bb_upper = float(latest.get("BB_Upper", close * 1.05))
    bb_lower = float(latest.get("BB_Lower", close * 0.95))
    atr = float(latest.get("ATR_14", close * 0.015))
    hist_vol = float(latest.get("Historical_Volatility", 18.0))

    # Signal interpretations
    rsi_signal = "Overbought" if rsi >= 70 else ("Oversold" if rsi <= 30 else "Neutral")
    macd_signal = "Bullish Crossover" if macd > macd_sig else "Bearish Divergence"
    trend_signal = "Bullish (Above SMA 20/50)" if close > sma_20 and close > sma_50 else (
        "Bearish (Below SMA 20/50)" if close < sma_20 and close < sma_50 else "Mixed / Consolidating"
    )

    indicators_data = {
        "price": close,
        "sma_20": {"value": sma_20, "signal": "Bullish" if close > sma_20 else "Bearish"},
        "sma_50": {"value": sma_50, "signal": "Bullish" if close > sma_50 else "Bearish"},
        "ema_20": {"value": ema_20, "signal": "Bullish" if close > ema_20 else "Bearish"},
        "rsi_14": {"value": rsi, "signal": rsi_signal},
        "macd": {"value": macd, "signal_line": macd_sig, "histogram": macd_hist, "signal": macd_signal},
        "bollinger_bands": {"upper": bb_upper, "middle": float(latest.get("BB_Middle", close)), "lower": bb_lower},
        "atr_14": {"value": atr},
        "historical_volatility": {"value": f"{hist_vol}%"},
        "overall_technical_bias": "Bullish" if (rsi > 50 and macd > macd_sig and close > sma_20) else (
            "Bearish" if (rsi < 50 and macd < macd_sig and close < sma_20) else "Neutral / Balanced"
        ),
        "explanations": {
            "RSI_14": f"Relative Strength Index is {rsi:.1f}. Values > 70 suggest overbought territory, while < 30 suggest oversold conditions. Current state: {rsi_signal}.",
            "MACD": f"MACD line ({macd:.2f}) vs Signal line ({macd_sig:.2f}). Histogram is {macd_hist:.2f}, indicating {macd_signal.lower()}.",
            "Moving_Averages": f"Price ₹{close:,.2f} is {'above' if close > sma_20 else 'below'} SMA 20 (₹{sma_20:,.2f}) and {'above' if close > sma_50 else 'below'} SMA 50 (₹{sma_50:,.2f}).",
            "Bollinger_Bands": f"Price is trading between Lower band ₹{bb_lower:,.2f} and Upper band ₹{bb_upper:,.2f}.",
            "ATR_14": f"Average True Range is ₹{atr:,.2f}, representing average daily volatility in rupee terms."
        }
    }
    return indicators_data
