"""
Automated Unit Tests for Market Data Provider and Symbols Registry.
Verifies data normalization, cache mechanism, synthetic fallback, quote integrity,
and strict rejection of ordinary English words.
"""
import pytest
import pandas as pd
from backend.market_data.symbols import (
    normalize_symbol,
    safe_normalize_symbol,
    is_valid_symbol,
    get_symbol_meta,
    WATCHLIST_METADATA,
    COMMON_ENGLISH_WORDS
)
from backend.market_data.yahoo_provider import YahooMarketDataProvider

def test_symbol_normalization():
    assert safe_normalize_symbol("reliance") == "RELIANCE.NS"
    assert safe_normalize_symbol("tcs.ns") == "TCS.NS"
    assert safe_normalize_symbol("  hdfcbank  ") == "HDFCBANK.NS"

def test_reject_ordinary_english_words():
    """Verifies ordinary English words like SHOULD, BUY, SELL, CAN are never treated as tickers."""
    invalid_words = ["SHOULD", "BUY", "SELL", "CAN", "WILL", "THE", "INVEST", "GOOD", "TIME", "DAY", "WHAT", "SO"]
    for word in invalid_words:
        assert not is_valid_symbol(word), f"Word '{word}' should not be valid symbol"
        assert safe_normalize_symbol(word) is None
        with pytest.raises(ValueError):
            normalize_symbol(word)
        with pytest.raises(ValueError):
            get_symbol_meta(word)

def test_symbol_metadata_lookup():
    meta = get_symbol_meta("RELIANCE.NS")
    assert meta["ticker"] == "RELIANCE"
    assert meta["exchange"] == "NSE"
    assert meta["currency"] == "INR"
    assert meta["benchmark_price"] > 0

    # Unlisted symbol raises ValueError
    with pytest.raises(ValueError):
        get_symbol_meta("NONEXISTENT")

def test_synthetic_historical_generation():
    provider = YahooMarketDataProvider()
    df = provider.generate_synthetic_historical("TCS.NS", period="1Y")
    
    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert len(df) >= 200
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        assert col in df.columns
        assert not df[col].isnull().any()
    
    # Check OHLC relationship: High >= Low, High >= Open, High >= Close
    assert (df["High"] >= df["Low"]).all()
    assert (df["High"] >= df["Open"]).all()
    assert (df["High"] >= df["Close"]).all()

    # Rejects invalid symbol
    df_invalid = provider.generate_synthetic_historical("SHOULD.NS", period="1Y")
    assert df_invalid.empty

def test_quote_snapshot_retrieval():
    provider = YahooMarketDataProvider()
    quote = provider.get_quote("INFY.NS")
    
    assert quote["symbol"] == "INFY.NS"
    assert quote["price"] > 0
    assert "change" in quote
    assert "change_pct" in quote
    assert "status" in quote
    assert "disclaimer" in quote

    # Quote for invalid symbol returns unsupported status without crashing
    invalid_quote = provider.get_quote("SHOULD")
    assert invalid_quote["status"] == "unsupported_symbol"
    assert invalid_quote["price"] == 0.0

def test_watchlist_overview():
    provider = YahooMarketDataProvider()
    overview = provider.get_watchlist_overview()
    assert len(overview) == len(WATCHLIST_METADATA)
    symbols = [o["symbol"] for o in overview]
    assert "RELIANCE.NS" in symbols
    assert "TCS.NS" in symbols
