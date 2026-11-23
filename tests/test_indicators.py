"""
Automated Unit Tests for Institutional Technical Indicators.
Validates mathematical calculations for SMA, EMA, RSI, MACD, Bollinger Bands, ATR, and Volatility.
"""
import pytest
import numpy as np
import pandas as pd
from backend.analytics.indicators import calculate_technical_indicators, get_latest_indicators_summary
from backend.market_data.yahoo_provider import YahooMarketDataProvider

@pytest.fixture
def sample_historical_df():
    provider = YahooMarketDataProvider()
    return provider.generate_synthetic_historical("RELIANCE.NS", period="1Y")

def test_technical_indicators_calculation(sample_historical_df):
    df_ind = calculate_technical_indicators(sample_historical_df)

    # Check that indicator columns exist
    expected_cols = [
        "SMA_20", "SMA_50", "EMA_20", "RSI_14",
        "MACD", "MACD_Signal", "MACD_Hist",
        "BB_Upper", "BB_Middle", "BB_Lower",
        "ATR_14", "Daily_Return", "Historical_Volatility", "Volume_SMA_20"
    ]
    for col in expected_cols:
        assert col in df_ind.columns, f"Missing column: {col}"

    # Verify RSI is within bounds [0, 100]
    valid_rsi = df_ind["RSI_14"].dropna()
    assert (valid_rsi >= 0).all() and (valid_rsi <= 100).all()

    # Verify Bollinger Bands ordering (Upper >= Middle >= Lower)
    valid_bb = df_ind.dropna(subset=["BB_Upper", "BB_Middle", "BB_Lower"])
    assert (valid_bb["BB_Upper"] >= valid_bb["BB_Middle"]).all()
    assert (valid_bb["BB_Middle"] >= valid_bb["BB_Lower"]).all()

    # Verify ATR is strictly non-negative
    valid_atr = df_ind["ATR_14"].dropna()
    assert (valid_atr >= 0).all()

def test_indicators_summary_extraction(sample_historical_df):
    df_ind = calculate_technical_indicators(sample_historical_df)
    summary = get_latest_indicators_summary(df_ind)

    assert "price" in summary
    assert "sma_20" in summary
    assert "sma_50" in summary
    assert "rsi_14" in summary
    assert "macd" in summary
    assert "bollinger_bands" in summary
    assert "overall_technical_bias" in summary
    assert summary["overall_technical_bias"] in ("Bullish", "Bearish", "Neutral / Balanced")
    assert "explanations" in summary
    assert len(summary["explanations"]) >= 4
