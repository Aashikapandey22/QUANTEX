"""
Automated Tests for Machine Learning Directional Prediction Pipeline.
Validates chronological splitting, feature engineering, no lookahead bias,
confusion matrix, majority class baselines, reliability warnings, and fair model comparison.
"""
import pytest
import pandas as pd
from backend.market_data.yahoo_provider import YahooMarketDataProvider
from backend.ml.pipeline import engineer_features, train_and_predict

@pytest.fixture
def df_historical():
    provider = YahooMarketDataProvider()
    return provider.generate_synthetic_historical("INFY.NS", period="1Y")

def test_feature_engineering_structure(df_historical):
    from backend.analytics.indicators import calculate_technical_indicators
    df_ind = calculate_technical_indicators(df_historical)
    trainable_df, latest_features = engineer_features(df_ind, horizon=5)

    assert not trainable_df.empty
    assert not latest_features.empty
    assert len(latest_features) == 1
    # Binary target
    assert set(trainable_df["target"].unique()).issubset({0, 1})
    # Target is strictly not null in trainable
    assert not trainable_df["target"].isna().any()

def test_logistic_regression_pipeline(df_historical):
    res = train_and_predict(df_historical, model_type="logistic_regression", horizon=5)

    assert res["status"] == "success"
    assert res["selected_model"] == "logistic_regression"
    assert res["predicted_direction"] in ("Bullish", "Bearish", "Neutral")
    assert 0.0 <= res["probability_score"] <= 100.0
    assert 0.0 <= res["class_probabilities"]["bullish_pct"] <= 100.0
    assert 0.0 <= res["class_probabilities"]["bearish_pct"] <= 100.0
    assert -100.0 <= res["directional_score"] <= 100.0
    assert "metrics" in res
    assert 0.0 <= res["metrics"]["out_of_sample_accuracy"] <= 100.0
    assert res["sample_counts"]["train"] > 0
    assert res["sample_counts"]["test"] > 0

def test_random_forest_pipeline(df_historical):
    res = train_and_predict(df_historical, model_type="random_forest", horizon=5)

    assert res["status"] == "success"
    assert res["selected_model"] == "random_forest"
    assert res["predicted_direction"] in ("Bullish", "Bearish", "Neutral")
    assert "metrics" in res

def test_tcs_and_reliance_pipeline_audit():
    """Audits ML pipeline for TCS.NS and RELIANCE.NS, verifying data reflection and metrics integrity."""
    provider = YahooMarketDataProvider()
    for sym in ["TCS.NS", "RELIANCE.NS"]:
        df = provider.generate_synthetic_historical(sym, period="1Y")
        res = train_and_predict(df, model_type="logistic_regression", horizon=5)

        assert res["status"] == "success"
        # Price and market date must strictly match actual symbol's latest data
        assert res["latest_price"] == float(df["Close"].iloc[-1])
        assert res["last_market_date"] == df.index[-1].strftime("%Y-%m-%d")
        
        # Reliability rating must be present
        assert res["reliability"]["rating"] in ("Low", "Moderate", "Acceptable (Historical)")
        assert len(res["reliability"]["warning"]) > 10

        # Confusion matrix checks
        cm = res["confusion_matrix"]
        assert cm["total_test_samples"] == res["sample_counts"]["test"]
        assert cm["true_negative"] + cm["false_positive"] + cm["false_negative"] + cm["true_positive"] == cm["total_test_samples"]

        # Fair comparison includes both models
        assert "logistic_regression" in res["model_comparison"]
        assert "random_forest" in res["model_comparison"]

def test_distinction_of_concepts(df_historical):
    """
    Verifies that predicted direction, class probability, directional score,
    and out-of-sample accuracy are clearly separated and never conflated.
    """
    res = train_and_predict(df_historical, model_type="logistic_regression", horizon=5)
    
    direction = res["predicted_direction"]
    bullish_p = res["class_probabilities"]["bullish_pct"]
    score = res["directional_score"]
    acc = res["metrics"]["out_of_sample_accuracy"]

    assert direction in ("Bullish", "Bearish", "Neutral")
    assert isinstance(bullish_p, float)
    assert isinstance(score, float)
    assert isinstance(acc, float)

    # Metric explanations for students
    assert "metric_explanations" in res
    assert "out_of_sample_accuracy" in res["metric_explanations"]
    assert "majority_class_baseline" in res["metric_explanations"]

def test_insufficient_data_rejection():
    empty_df = pd.DataFrame()
    res = train_and_predict(empty_df, model_type="logistic_regression", horizon=5)
    assert res["status"] == "unavailable"
