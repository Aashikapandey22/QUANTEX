"""
Machine Learning Directional Prediction Pipeline.
Trains supervised classification models (Logistic Regression baseline & Random Forest)
on historical technical indicator features with strict chronological splitting
to avoid look-ahead bias and temporal leakage.
Provides honest out-of-sample metrics, model reliability ratings, confusion matrices,
majority-class baselines, and pedagogical metric explanations.
"""
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

from backend.analytics.indicators import calculate_technical_indicators

logger = logging.getLogger("quantex.ml")

FEATURE_COLUMNS = [
    "return_lag1",
    "return_lag5",
    "sma20_ratio",
    "sma50_ratio",
    "ema20_ratio",
    "rsi_14",
    "macd",
    "macd_hist",
    "atr_ratio",
    "hist_vol",
    "vol_ratio"
]

METRIC_EXPLANATIONS = {
    "out_of_sample_accuracy": (
        "Accuracy is the proportion of correct directional forecasts over all test samples: "
        "(TP + TN) / Total. In financial time series, accuracy must be evaluated strictly on unseen "
        "chronological test data, not on training data."
    ),
    "precision": (
        "Precision measures directional reliability: of all times the model predicted a Bullish rise, "
        "what percentage actually moved upward? TP / (TP + FP). High precision minimizes false alarms."
    ),
    "recall": (
        "Recall measures capture rate: of all actual upward moves in the test period, what percentage "
        "did the model identify? TP / (TP + FN). High recall minimizes missed opportunities."
    ),
    "f1_score": (
        "F1-score is the harmonic mean of Precision and Recall: 2 * (P * R) / (P + R). "
        "It provides a balanced measure when directional classes are imbalanced."
    ),
    "majority_class_baseline": (
        "The naive baseline accuracy achieved by always guessing the most frequent class from the training set. "
        "A model that fails to beat the majority class baseline provides zero practical predictive edge."
    ),
    "class_probability": (
        "The model's internal probability estimate P(Up) vs P(Down) for the latest market bar. "
        "Note: Raw class probabilities are model score distributions, NOT calibrated win guarantees."
    ),
    "chronological_split": (
        "Financial data must be split by time (e.g. first 80% train, last 20% test). "
        "Random shuffling causes future price leakage into the past (look-ahead bias) and is strictly invalid."
    ),
    "confusion_matrix": (
        "A 2x2 contingency table: True Negatives (Bearish correct), False Positives (Bullish false alarms), "
        "False Negatives (Missed Bullish moves), and True Positives (Bullish correct)."
    )
}

def engineer_features(df_with_ind: pd.DataFrame, horizon: int = 5) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Constructs normalized features and directional target.
    Target: 1 if Close(t + horizon) > Close(t), 0 if <=, and NaN for the final horizon rows.
    Returns:
    - trainable_df: rows where both features and future target are observed
    - latest_feature_row: the very latest market bar for forward inference
    """
    df = df_with_ind.copy()
    close = df["Close"].astype(float)

    # 1. Stationary Ratios and Return Lags
    df["return_lag1"] = close.pct_change(1)
    df["return_lag5"] = close.pct_change(5)
    df["sma20_ratio"] = (close / df["SMA_20"]) - 1.0
    df["sma50_ratio"] = (close / df["SMA_50"]) - 1.0
    df["ema20_ratio"] = (close / df["EMA_20"]) - 1.0
    df["rsi_14"] = df["RSI_14"] / 100.0  # scaled 0-1
    df["macd"] = df["MACD"] / close
    df["macd_hist"] = df["MACD_Hist"] / close
    df["atr_ratio"] = df["ATR_14"] / close
    df["hist_vol"] = df["Historical_Volatility"] / 100.0
    df["vol_ratio"] = (df["Volume"] / df["Volume_SMA_20"].replace(0, 1.0)).clip(0, 5.0)

    # 2. Future target formulation (Strictly h days ahead)
    future_close = close.shift(-horizon)
    # Target is 1 if future close > current close, 0 otherwise; NaN for last horizon rows
    df["target"] = np.where(future_close.isna(), np.nan, (future_close > close).astype(float))

    # Drop rows where features are NaN (e.g. initial indicator warmup window)
    feature_ready_df = df.dropna(subset=FEATURE_COLUMNS).copy()

    # Latest row for forward-looking prediction (target is unknown)
    latest_feature_row = feature_ready_df.iloc[[-1]][FEATURE_COLUMNS].copy()

    # Trainable rows: where both features AND target are known
    trainable_df = feature_ready_df.dropna(subset=["target"]).copy()
    trainable_df["target"] = trainable_df["target"].astype(int)

    return trainable_df, latest_feature_row

def train_and_predict(
    df: pd.DataFrame,
    model_type: str = "logistic_regression",
    horizon: int = 5,
    test_split_ratio: float = 0.2
) -> dict:
    """
    Executes an honest, scientifically sound ML prediction pipeline:
    1. Feature engineering on OHLCV series
    2. Strict chronological train/test split (no random shuffling)
    3. Fair comparison of both Logistic Regression AND Random Forest on the identical test split
    4. Out-of-sample evaluation: Accuracy, Precision, Recall, F1, and Confusion Matrix
    5. Baseline comparison against Majority Class and Random Chance
    6. Objective model reliability classification with honest warnings
    7. Detailed student explanations for all metrics
    """
    if df.empty or len(df) < 60:
        return {
            "status": "unavailable",
            "message": "Insufficient historical data (minimum 60 bars required for training).",
            "predicted_direction": "Unavailable"
        }

    df_ind = calculate_technical_indicators(df)
    trainable_df, latest_features = engineer_features(df_ind, horizon=horizon)

    if len(trainable_df) < 40:
        return {
            "status": "unavailable",
            "message": "Insufficient valid feature samples after indicator warmup.",
            "predicted_direction": "Unavailable"
        }

    X = trainable_df[FEATURE_COLUMNS]
    y = trainable_df["target"]

    # 1. Strict Chronological Split (No random shuffling)
    split_idx = int(len(X) * (1 - test_split_ratio))
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

    if len(y_test) < 5 or len(y_train) < 20:
        return {
            "status": "unavailable",
            "message": "Chronological test partition is too small for statistical evaluation.",
            "predicted_direction": "Unavailable"
        }

    train_dates = {
        "start": X_train.index[0].strftime("%Y-%m-%d") if isinstance(X_train.index[0], pd.Timestamp) else str(X_train.index[0]),
        "end": X_train.index[-1].strftime("%Y-%m-%d") if isinstance(X_train.index[-1], pd.Timestamp) else str(X_train.index[-1]),
        "sample_count": len(X_train)
    }
    test_dates = {
        "start": X_test.index[0].strftime("%Y-%m-%d") if isinstance(X_test.index[0], pd.Timestamp) else str(X_test.index[0]),
        "end": X_test.index[-1].strftime("%Y-%m-%d") if isinstance(X_test.index[-1], pd.Timestamp) else str(X_test.index[-1]),
        "sample_count": len(X_test)
    }

    # 2. Scaler fitted ONLY on training partition to prevent look-ahead bias
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    latest_scaled = scaler.transform(latest_features)

    # 3. Naive Baseline: Majority Class in Training Set
    majority_class_train = int(y_train.mode()[0])
    majority_class_name = "Bullish (Up)" if majority_class_train == 1 else "Bearish (Down)"
    naive_predictions = np.full(shape=len(y_test), fill_value=majority_class_train)
    majority_baseline_acc = float(accuracy_score(y_test, naive_predictions) * 100.0)

    # 4. Train Both Models Fairly on the Identical Chronological Splits
    models = {
        "logistic_regression": {
            "instance": LogisticRegression(C=1.0, max_iter=500, random_state=42),
            "display_name": "Logistic Regression (L2 Regularized Baseline)"
        },
        "random_forest": {
            "instance": RandomForestClassifier(n_estimators=100, max_depth=4, min_samples_split=5, random_state=42),
            "display_name": "Random Forest Classifier (Ensemble)"
        }
    }

    model_evaluations = {}
    for m_key, m_info in models.items():
        m = m_info["instance"]
        m.fit(X_train_scaled, y_train)

        # Out-of-sample predictions
        y_pred = m.predict(X_test_scaled)
        prob_test = m.predict_proba(X_test_scaled)
        acc = float(accuracy_score(y_test, y_pred) * 100.0)
        prec = float(precision_score(y_test, y_pred, zero_division=0) * 100.0)
        rec = float(recall_score(y_test, y_pred, zero_division=0) * 100.0)
        f1 = float(f1_score(y_test, y_pred, zero_division=0) * 100.0)

        # Confusion Matrix [TN, FP], [FN, TP]
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        tn, fp, fn, tp = int(cm[0, 0]), int(cm[0, 1]), int(cm[1, 0]), int(cm[1, 1])

        # Inference on latest market bar
        latest_probs = m.predict_proba(latest_scaled)[0]
        bearish_p = float(latest_probs[0])
        bullish_p = float(latest_probs[1])

        if bullish_p >= 0.55:
            direction = "Bullish"
        elif bullish_p <= 0.45:
            direction = "Bearish"
        else:
            direction = "Neutral"

        # Directional Score: signed confidence measure [-100 to +100]
        directional_score = round((bullish_p - 0.5) * 200, 1)

        model_evaluations[m_key] = {
            "model_type": m_key,
            "display_name": m_info["display_name"],
            "predicted_direction": direction,
            "directional_score": directional_score,
            "class_probabilities": {
                "bullish_pct": round(bullish_p * 100.0, 1),
                "bearish_pct": round(bearish_p * 100.0, 1)
            },
            "metrics": {
                "out_of_sample_accuracy": round(acc, 2),
                "precision": round(prec, 2),
                "recall": round(rec, 2),
                "f1_score": round(f1, 2),
                "edge_over_majority_baseline": round(acc - majority_baseline_acc, 2),
                "edge_over_random_chance": round(acc - 50.0, 2)
            },
            "confusion_matrix": {
                "true_negative": tn,
                "false_positive": fp,
                "false_negative": fn,
                "true_positive": tp,
                "total_test_samples": len(y_test)
            }
        }

    # Selected model output
    active_key = model_type if model_type in model_evaluations else "logistic_regression"
    active_eval = model_evaluations[active_key]

    # 5. Model Reliability Assessment based on Honest Out-of-Sample Performance
    active_acc = active_eval["metrics"]["out_of_sample_accuracy"]
    if active_acc < 50.0 or active_acc < majority_baseline_acc:
        reliability = "Low"
        reliability_level = "weak"
        reliability_warning = (
            f"Low predictive reliability – out-of-sample accuracy ({active_acc:.1f}%) is below random chance (50.0%) "
            f"or naive majority baseline ({majority_baseline_acc:.1f}%). Educational estimate only; do not base financial decisions on this model."
        )
    elif active_acc < (majority_baseline_acc + 5.0):
        reliability = "Moderate"
        reliability_level = "moderate"
        reliability_warning = (
            f"Moderate predictive reliability – model accuracy ({active_acc:.1f}%) shows a marginal historical edge "
            f"over baseline ({majority_baseline_acc:.1f}%). Highly susceptible to macro regime changes and volatility spikes."
        )
    else:
        reliability = "Acceptable (Historical)"
        reliability_level = "acceptable"
        reliability_warning = (
            f"Acceptable out-of-sample accuracy ({active_acc:.1f}%) on historical chronological test partition. "
            "Past empirical performance does not guarantee future live returns."
        )

    # Latest stock quote details
    latest_close = float(df["Close"].iloc[-1])
    last_date = df.index[-1].strftime("%Y-%m-%d") if isinstance(df.index[-1], pd.Timestamp) else str(df.index[-1])

    return {
        "status": "success",
        "selected_model": active_key,
        "model_name": active_eval["display_name"],
        "prediction_horizon_days": horizon,
        "latest_price": latest_close,
        "last_market_date": last_date,
        # Distinctly separated prediction concepts:
        "predicted_direction": active_eval["predicted_direction"],
        "class_probabilities": active_eval["class_probabilities"],
        "directional_score": active_eval["directional_score"],
        "probability_score": active_eval["class_probabilities"]["bullish_pct"] if active_eval["predicted_direction"] == "Bullish" else active_eval["class_probabilities"]["bearish_pct"],
        "bullish_probability": active_eval["class_probabilities"]["bullish_pct"],
        "bearish_probability": active_eval["class_probabilities"]["bearish_pct"],
        # Out-of-sample evaluation metrics:
        "metrics": active_eval["metrics"],
        "confusion_matrix": active_eval["confusion_matrix"],
        # Baselines:
        "baselines": {
            "majority_class_name": majority_class_name,
            "majority_class_baseline_accuracy": round(majority_baseline_acc, 2),
            "random_chance_baseline_accuracy": 50.0
        },
        # Reliability & Warning Indicators:
        "reliability": {
            "rating": reliability,
            "level": reliability_level,
            "warning": reliability_warning,
            "is_weak": reliability_level == "weak"
        },
        # Chronological Sample Breakdown:
        "sample_counts": {
            "train": train_dates["sample_count"],
            "test": test_dates["sample_count"],
            "total_samples": train_dates["sample_count"] + test_dates["sample_count"]
        },
        "period_dates": {
            "train": train_dates,
            "test": test_dates
        },
        # Fair Side-by-Side Model Comparison:
        "model_comparison": {
            "logistic_regression": {
                "name": "Logistic Regression",
                "direction": model_evaluations["logistic_regression"]["predicted_direction"],
                "p_bullish": model_evaluations["logistic_regression"]["class_probabilities"]["bullish_pct"],
                "accuracy": model_evaluations["logistic_regression"]["metrics"]["out_of_sample_accuracy"],
                "precision": model_evaluations["logistic_regression"]["metrics"]["precision"],
                "f1_score": model_evaluations["logistic_regression"]["metrics"]["f1_score"]
            },
            "random_forest": {
                "name": "Random Forest",
                "direction": model_evaluations["random_forest"]["predicted_direction"],
                "p_bullish": model_evaluations["random_forest"]["class_probabilities"]["bullish_pct"],
                "accuracy": model_evaluations["random_forest"]["metrics"]["out_of_sample_accuracy"],
                "precision": model_evaluations["random_forest"]["metrics"]["precision"],
                "f1_score": model_evaluations["random_forest"]["metrics"]["f1_score"]
            }
        },
        "features_used": FEATURE_COLUMNS,
        "metric_explanations": METRIC_EXPLANATIONS,
        "disclaimer": (
            "Probabilistic statistical classification trained strictly on historical features without lookahead. "
            "Class probability represents model score distribution, NOT guaranteed win rate or calibrated confidence. "
            "Educational and research use only. Never financial advice."
        )
    }
