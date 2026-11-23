"""
Yahoo Finance Market Data Provider for Indian Equities.
Includes SQLite caching, rate limiting handling, missing data sanitization,
clear data status indicators (delayed / historical / sample / cached),
and deterministic offline fallback data generation for isolated testing or network downtime.
"""
import time
import json
import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf

from config import Config
from backend.database import get_db_connection
from backend.market_data.base import MarketDataProvider
from backend.market_data.symbols import (
    normalize_symbol,
    safe_normalize_symbol,
    is_valid_symbol,
    get_symbol_meta,
    WATCHLIST_METADATA
)

logger = logging.getLogger("quantex.market_data")

PERIOD_DAYS_MAP = {
    "1M": 30,
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "2Y": 730
}

PERIOD_YF_MAP = {
    "1M": "1mo",
    "3M": "3mo",
    "6M": "6mo",
    "1Y": "1y",
    "2Y": "2y"
}

class YahooMarketDataProvider(MarketDataProvider):
    def __init__(self, cache_ttl: int = None):
        self.cache_ttl = cache_ttl or Config.CACHE_TTL_SECONDS

    def _get_cached_history(self, symbol: str, period: str):
        """Attempts to retrieve cached historical data from SQLite."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cache_key = f"hist_{symbol}_{period}"
            cursor.execute(
                "SELECT data_json, timestamp FROM market_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            conn.close()

            if row:
                cached_time = row["timestamp"]
                if (time.time() - cached_time) < self.cache_ttl:
                    data = json.loads(row["data_json"])
                    df = pd.DataFrame(data)
                    if not df.empty and "Date" in df.columns:
                        df["Date"] = pd.to_datetime(df["Date"])
                        df = df.set_index("Date")
                    return df, "cached"
        except Exception as e:
            logger.warning(f"Cache read error for {symbol}: {e}")
        return None, None

    def _set_cached_history(self, symbol: str, period: str, df: pd.DataFrame):
        """Saves historical data to SQLite cache."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cache_key = f"hist_{symbol}_{period}"
            
            # Export dataframe with Date column as string
            export_df = df.reset_index()
            export_df["Date"] = export_df["Date"].astype(str)
            data_json = export_df.to_json(orient="records")

            cursor.execute("""
                INSERT OR REPLACE INTO market_cache (cache_key, symbol, period, data_json, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (cache_key, symbol, period, data_json, time.time()))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Cache write error for {symbol}: {e}")

    def generate_synthetic_historical(self, symbol: str, period: str = "1Y") -> pd.DataFrame:
        """
        Generates realistic, deterministic historical OHLCV data using a geometric Brownian motion
        grounded in the stock's actual benchmark valuation.
        Used for isolated testing or when external API is unreachable.
        """
        norm_symbol = safe_normalize_symbol(symbol)
        if not norm_symbol or norm_symbol not in WATCHLIST_METADATA:
            return pd.DataFrame()

        meta = WATCHLIST_METADATA[norm_symbol]
        base_price = meta.get("benchmark_price", 1000.0)
        days = PERIOD_DAYS_MAP.get(period, 365)
        
        # Deterministic seed based on symbol name
        seed = sum(ord(c) for c in symbol)
        rng = np.random.default_rng(seed)

        end_date = datetime.now()
        # Generate trading days (Mon-Fri)
        dates = pd.date_range(end=end_date, periods=int(days * 1.45), freq="B")[-days:]
        
        # Geometric brownian motion parameters
        dt = 1 / 252.0
        mu = 0.12  # 12% annual drift for Indian equities
        sigma = 0.22  # 22% annualized volatility
        
        daily_returns = np.exp((mu - 0.5 * sigma**2) * dt + sigma * np.sqrt(dt) * rng.standard_normal(len(dates)))
        price_path = base_price * np.cumprod(daily_returns)
        # Scale path so last price is near benchmark
        scale = base_price / price_path[-1]
        closes = price_path * (0.9 + 0.1 * scale)

        opens = []
        highs = []
        lows = []
        volumes = []

        for i, close in enumerate(closes):
            prev_close = closes[i-1] if i > 0 else close
            # Open is close to previous close with small overnight gap
            open_p = prev_close * (1 + rng.normal(0, 0.004))
            intra_std = close * 0.012
            high_p = max(open_p, close) + abs(rng.normal(0, intra_std))
            low_p = min(open_p, close) - abs(rng.normal(0, intra_std))
            # Keep low positive
            low_p = max(low_p, 1.0)
            vol = int(rng.normal(1200000, 300000))
            vol = max(vol, 50000)

            opens.append(round(float(open_p), 2))
            highs.append(round(float(high_p), 2))
            lows.append(round(float(low_p), 2))
            volumes.append(vol)

        df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": [round(float(c), 2) for c in closes],
            "Volume": volumes
        })
        df = df.set_index("Date")
        return df

    def get_historical_data(self, symbol: str, period: str = "1Y") -> tuple[pd.DataFrame, dict]:
        """
        Fetches historical data from yfinance with cache fallback.
        Returns (DataFrame, status_metadata).
        """
        norm_symbol = safe_normalize_symbol(symbol)
        if not norm_symbol:
            return pd.DataFrame(), {
                "source": "none",
                "status": "unsupported_symbol",
                "disclaimer": f"'{symbol}' is not a recognized Indian equity symbol.",
                "last_market_date": "N/A",
                "is_fallback": False
            }

        yf_period = PERIOD_YF_MAP.get(period, "1y")

        # 1. Check Cache
        cached_df, source = self._get_cached_history(norm_symbol, period)
        if cached_df is not None and not cached_df.empty:
            last_date = cached_df.index[-1].strftime("%Y-%m-%d") if isinstance(cached_df.index[-1], pd.Timestamp) else str(cached_df.index[-1])
            return cached_df, {
                "source": "cached",
                "status": "cached",
                "disclaimer": "Data served from local cache. Market prices are delayed/historical, not real-time exchange feeds.",
                "last_market_date": last_date,
                "is_fallback": False
            }

        # 2. Try Live Yahoo Finance
        try:
            ticker = yf.Ticker(norm_symbol)
            df = ticker.history(period=yf_period, auto_adjust=True, timeout=8)
            if df is not None and not df.empty and len(df) > 5:
                # Sanitize columns
                df = df.reset_index()
                # yfinance returns Date column with tz awareness sometimes
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
                    df = df.set_index("Date")
                
                required_cols = ["Open", "High", "Low", "Close", "Volume"]
                df = df[[c for c in required_cols if c in df.columns]]
                # Drop rows with NaN in Close
                df.dropna(subset=["Close"], inplace=True)
                
                # Round to 2 decimals
                df["Open"] = df["Open"].round(2)
                df["High"] = df["High"].round(2)
                df["Low"] = df["Low"].round(2)
                df["Close"] = df["Close"].round(2)
                df["Volume"] = df["Volume"].astype(int)

                # Cache fresh result
                self._set_cached_history(norm_symbol, period, df)
                last_date = df.index[-1].strftime("%Y-%m-%d")
                return df, {
                    "source": "yfinance",
                    "status": "delayed",
                    "disclaimer": "Yahoo Finance historical market data. Typically delayed by 15-20 minutes. Not exchange-authoritative.",
                    "last_market_date": last_date,
                    "is_fallback": False
                }
        except Exception as e:
            logger.warning(f"Yahoo Finance fetch error for {norm_symbol}: {e}. Falling back to deterministic model.")

        # 3. Fallback to high-fidelity synthetic model
        fallback_df = self.generate_synthetic_historical(norm_symbol, period)
        last_date = fallback_df.index[-1].strftime("%Y-%m-%d")
        return fallback_df, {
            "source": "synthetic_model",
            "status": "sample",
            "disclaimer": "Offline/Simulated educational data grounded in benchmark price. Live feed unavailable.",
            "last_market_date": last_date,
            "is_fallback": True
        }

    def get_quote(self, symbol: str) -> dict:
        """
        Returns latest quote snapshot with price, change, change_pct, high, low, volume,
        and data status attributes.
        """
        norm_symbol = safe_normalize_symbol(symbol)
        if not norm_symbol:
            return {
                "symbol": symbol,
                "name": "Unknown Instrument",
                "sector": "N/A",
                "price": 0.0,
                "change": 0.0,
                "change_pct": 0.0,
                "open": 0.0,
                "high": 0.0,
                "low": 0.0,
                "volume": 0,
                "last_market_date": "N/A",
                "status": "unsupported_symbol",
                "disclaimer": f"'{symbol}' is not a recognized Indian equity symbol.",
                "is_fallback": False
            }

        meta = get_symbol_meta(norm_symbol)
        df, status_info = self.get_historical_data(norm_symbol, period="1M")

        if df.empty or len(df) < 2:
            return {
                "symbol": norm_symbol,
                "name": meta["name"],
                "sector": meta["sector"],
                "price": meta["benchmark_price"],
                "change": 0.0,
                "change_pct": 0.0,
                "open": meta["benchmark_price"],
                "high": meta["benchmark_price"],
                "low": meta["benchmark_price"],
                "volume": 0,
                "last_market_date": datetime.now().strftime("%Y-%m-%d"),
                "status": "sample",
                "disclaimer": status_info.get("disclaimer", "Sample baseline data")
            }

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        price = float(latest["Close"])
        prev_close = float(prev["Close"])
        change = round(price - prev_close, 2)
        change_pct = round((change / prev_close) * 100, 2) if prev_close > 0 else 0.0

        return {
            "symbol": norm_symbol,
            "ticker": meta["ticker"],
            "name": meta["name"],
            "sector": meta["sector"],
            "exchange": meta["exchange"],
            "currency": meta["currency"],
            "price": price,
            "change": change,
            "change_pct": change_pct,
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": price,
            "volume": int(latest["Volume"]),
            "last_market_date": df.index[-1].strftime("%Y-%m-%d"),
            "status": status_info["status"],
            "disclaimer": status_info["disclaimer"],
            "is_fallback": status_info.get("is_fallback", False)
        }

    def get_watchlist_overview(self) -> list:
        """Fetches quotes for all 10 default watchlist symbols."""
        results = []
        for sym in Config.DEFAULT_WATCHLIST:
            try:
                q = self.get_quote(sym)
                results.append(q)
            except Exception as e:
                logger.error(f"Failed to get quote for {sym}: {e}")
        return results

# Singleton instance
market_data_provider = YahooMarketDataProvider()
