# MACHINE LEARNING METHODOLOGY & MATHEMATICAL FORMULATION

## 1. Problem Formulation

The objective is to estimate the probability of an upward or downward price movement of an Indian equity over a future horizon of $h$ trading days (default: $h = 5$ days):

$$y_t = \begin{cases} 1 & \text{if } C_{t+h} > C_t \\ 0 & \text{if } C_{t+h} \le C_t \end{cases}$$

where $C_t$ represents the split- and dividend-adjusted closing price on trading day $t$.

---

## 2. Engineered Stationary Features

Financial time series exhibit non-stationarity. Raw prices cannot be directly used as features. QUANTEX engineers 11 stationary relative ratios and oscillator features:

1. `return_lag1`: 1-day percentage return $\frac{C_t - C_{t-1}}{C_{t-1}}$
2. `return_lag5`: 5-day percentage return $\frac{C_t - C_{t-5}}{C_{t-5}}$
3. `sma20_ratio`: Price distance from 20-day SMA $\frac{C_t}{\text{SMA}_{20}(t)} - 1$
4. `sma50_ratio`: Price distance from 50-day SMA $\frac{C_t}{\text{SMA}_{50}(t)} - 1$
5. `ema20_ratio`: Price distance from 20-day EMA $\frac{C_t}{\text{EMA}_{20}(t)} - 1$
6. `rsi_14`: Normalized Relative Strength Index $\frac{\text{RSI}_{14}(t)}{100}$
7. `macd`: MACD line scaled by price $\frac{\text{MACD}(t)}{C_t}$
8. `macd_hist`: MACD Histogram scaled by price $\frac{\text{Hist}(t)}{C_t}$
9. `atr_ratio`: Average True Range normalized by price $\frac{\text{ATR}_{14}(t)}{C_t}$
10. `hist_vol`: 20-day annualized log-return volatility
11. `vol_ratio`: Volume scaled by 20-day volume moving average $\frac{V_t}{\text{SMA}_{20}(V_t)}$

---

## 3. Prevention of Look-Ahead Bias & Temporal Leakage

- **Strict Chronological Train/Test Split**:
  - Training Set: First 80% of chronological observations ($t = 1 \dots T_{\text{split}}$)
  - Testing Set: Last 20% of chronological observations ($t = T_{\text{split}}+1 \dots T - h$)
  - **Random shuffling is strictly prohibited** ($k$-fold CV with random shuffling causes future-to-past data leakage).
- **Target Horizon Exclusion**: The final $h$ bars of historical data have unobserved future targets and are reserved exclusively for out-of-sample forward inference.
- **Scaler Fit**: `StandardScaler` is fitted exclusively on the training subset and applied to the test set.

---

## 4. Model Architectures & Evaluation

- **Baseline Model**: $L_2$-Regularized Logistic Regression with calibrated sigmoid probability output.
- **Alternative Model**: Random Forest Classifier (100 estimators, max depth 4 to prevent overfitting).
- **Evaluation Metrics Reported**:
  - Accuracy: $\frac{TP + TN}{TP + TN + FP + FN}$
  - Precision: $\frac{TP}{TP + FP}$
  - Recall: $\frac{TP}{TP + FN}$
  - $F_1$-Score: $2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$
