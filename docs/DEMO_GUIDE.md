# DEMO PRESENTATION GUIDE FOR EVALUATORS

This guide provides a structured 5-minute demonstration script for showcasing QUANTEX to evaluators, faculty, or interviewers.

---

## Demo Step-by-Step Script

### Step 1: Launch Application & Overview Terminal (1 Min)
1. Run `python3 app.py` in the terminal.
2. Open `http://127.0.0.1:5001`.
3. Highlight the institutional design system: charcoal palette, live ticker tape, 10 Indian equities on the NSE, and virtual capital pill (₹10,00,000).
4. Demonstrate the interactive financial chart: green/red candlesticks, volume sub-panel, SMA 20/50 overlays, and timeframe switcher (1M, 3M, 6M, 1Y).

### Step 2: Autonomous AI Agent & Voice Assistant (1.5 Mins)
1. Click the **AI Terminal** button on the top right.
2. Click the prompt chip: `"Analyse RELIANCE"`.
3. Point out the transparent **PLAN → ACT → OBSERVE → RESPOND** execution badges.
4. Show the tool telemetry box displaying which backend functions were executed.
5. Demonstrate voice interaction: click the 🎙 button and say *"Predict TCS"* or click the chip.

### Step 3: Machine Learning Directional Forecasting (1 Min)
1. Navigate to the **AI Predictions** tab.
2. Select `TCS.NS`, algorithm `Random Forest`, and horizon `5 Days`.
3. Click `Execute ML Prediction`.
4. Point out:
   - Chronological train/test split (zero future leakage).
   - Probability score and directional bias.
   - Out-of-sample metrics (Accuracy, Precision, Recall, F1).
   - Transparent list of 11 engineered stationary features.

### Step 4: Quantitative Strategy Backtesting (45 Secs)
1. Navigate to the **Backtesting** tab.
2. Run an SMA (20/50) Crossover simulation on `INFY.NS`.
3. Explain the execution modeling: next-bar execution price, 0.05% slippage, 0.1% fees.
4. Review the generated Equity Curve vs Buy & Hold benchmark and the chronological executed trade ledger.

### Step 5: Virtual Paper Trading & Risk Management (45 Secs)
1. Navigate to the **Paper Trading** tab.
2. Place a virtual BUY order for 25 shares of `RELIANCE.NS`.
3. Show immediate deduction of cash, creation of holding, and calculation of unrealized P&L.
4. Switch to **Risk Management** to show updated 95% Parametric VaR, Herfindahl-Hirschman concentration (HHI), and adverse market stress-test scenarios (-2%, -5%, -10%).
