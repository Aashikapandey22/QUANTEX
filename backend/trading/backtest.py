"""
Quantitative Strategy Backtesting Engine.
Simulates chronological trading of Moving Average Crossover strategies with next-bar execution,
slippage, transaction costs, and institutional performance metrics.
"""
import numpy as np
import pandas as pd
from backend.analytics.indicators import calculate_technical_indicators

def run_ma_crossover_backtest(
    df: pd.DataFrame,
    fast_period: int = 20,
    slow_period: int = 50,
    initial_capital: float = 1000000.0,
    fee_pct: float = 0.001,  # 0.1% per trade
    slippage_pct: float = 0.0005  # 0.05% slippage
) -> dict:
    """
    Backtests an SMA Crossover Strategy:
    - Signal: BUY when Fast SMA crosses above Slow SMA.
    - Signal: SELL when Fast SMA crosses below Slow SMA.
    - Strict next-bar execution: trade executes on bar t+1 after signal generated on bar t.
    """
    if df.empty or len(df) < slow_period + 5:
        return {
            "status": "error",
            "message": f"Insufficient historical bars (need at least {slow_period + 10} bars)."
        }

    data = df.copy()
    close = data["Close"].astype(float)
    data["SMA_Fast"] = close.rolling(window=fast_period, min_periods=fast_period).mean()
    data["SMA_Slow"] = close.rolling(window=slow_period, min_periods=slow_period).mean()

    # Identify crossover signals on bar t
    # 1: Long Signal, -1: Exit/Short Signal, 0: Neutral
    data["Signal"] = 0
    crossover_long = (data["SMA_Fast"] > data["SMA_Slow"]) & (data["SMA_Fast"].shift(1) <= data["SMA_Slow"].shift(1))
    crossover_short = (data["SMA_Fast"] < data["SMA_Slow"]) & (data["SMA_Fast"].shift(1) >= data["SMA_Slow"].shift(1))
    
    data.loc[crossover_long, "Signal"] = 1
    data.loc[crossover_short, "Signal"] = -1

    # Shift signal to next bar for realistic next-bar execution (no look-ahead)
    data["Exec_Signal"] = data["Signal"].shift(1).fillna(0)

    # Simulation Variables
    capital = initial_capital
    position = 0  # number of shares
    entry_price = 0.0
    entry_date = None
    trades = []
    equity_curve = []
    buy_hold_equity = []

    first_close = float(close.iloc[slow_period])
    buy_hold_shares = initial_capital / first_close

    for i in range(slow_period, len(data)):
        bar = data.iloc[i]
        date_str = data.index[i].strftime("%Y-%m-%d") if isinstance(data.index[i], pd.Timestamp) else str(data.index[i])
        curr_price = float(bar["Close"])
        exec_sig = int(bar["Exec_Signal"])

        # Execute BUY
        if exec_sig == 1 and position == 0:
            effective_price = curr_price * (1 + slippage_pct)
            fee = capital * fee_pct
            investable = capital - fee
            position = int(investable // effective_price)
            if position > 0:
                cost = position * effective_price
                capital = capital - cost - fee
                entry_price = effective_price
                entry_date = date_str

        # Execute SELL
        elif exec_sig == -1 and position > 0:
            effective_price = curr_price * (1 - slippage_pct)
            gross_val = position * effective_price
            fee = gross_val * fee_pct
            capital += (gross_val - fee)
            
            pnl = (effective_price - entry_price) * position - (fee * 2)
            pnl_pct = ((effective_price - entry_price) / entry_price) * 100
            
            trades.append({
                "entry_date": entry_date,
                "exit_date": date_str,
                "entry_price": round(entry_price, 2),
                "exit_price": round(effective_price, 2),
                "shares": position,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "is_win": pnl > 0
            })
            position = 0
            entry_price = 0.0

        # Mark-to-market total portfolio value
        curr_val = capital + (position * curr_price)
        bh_val = buy_hold_shares * curr_price
        
        equity_curve.append({
            "date": date_str,
            "portfolio_value": round(curr_val, 2),
            "benchmark_value": round(bh_val, 2)
        })

    # Close open position at the end of backtest period
    if position > 0:
        last_price = float(data["Close"].iloc[-1]) * (1 - slippage_pct)
        gross_val = position * last_price
        fee = gross_val * fee_pct
        capital += (gross_val - fee)
        pnl = (last_price - entry_price) * position - (fee * 2)
        pnl_pct = ((last_price - entry_price) / entry_price) * 100
        trades.append({
            "entry_date": entry_date,
            "exit_date": data.index[-1].strftime("%Y-%m-%d"),
            "entry_price": round(entry_price, 2),
            "exit_price": round(last_price, 2),
            "shares": position,
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "is_win": pnl > 0
        })
        position = 0

    final_capital = equity_curve[-1]["portfolio_value"] if equity_curve else capital
    total_return_pct = ((final_capital - initial_capital) / initial_capital) * 100
    
    # Buy & Hold Return
    bh_final = equity_curve[-1]["benchmark_value"] if equity_curve else initial_capital
    bh_return_pct = ((bh_final - initial_capital) / initial_capital) * 100

    # Max Drawdown Calculation
    eq_series = pd.Series([e["portfolio_value"] for e in equity_curve])
    cum_max = eq_series.cummax()
    drawdown = (eq_series - cum_max) / cum_max
    max_drawdown_pct = float(abs(drawdown.min()) * 100) if not drawdown.empty else 0.0

    # Sharpe Ratio (daily risk-free rate assumed 6% per annum for India)
    daily_returns = eq_series.pct_change().dropna()
    rf_daily = (1 + 0.06)**(1/252) - 1
    excess_returns = daily_returns - rf_daily
    if len(daily_returns) > 5 and daily_returns.std() > 0:
        sharpe_ratio = float((excess_returns.mean() / daily_returns.std()) * np.sqrt(252))
    else:
        sharpe_ratio = 0.0

    # Trade stats
    total_trades = len(trades)
    winning_trades = sum(1 for t in trades if t["is_win"])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    # CAGR
    days_span = len(equity_curve)
    years = max(days_span / 252.0, 0.1)
    cagr = (((final_capital / initial_capital) ** (1 / years)) - 1) * 100 if final_capital > 0 else -100.0

    return {
        "status": "success",
        "strategy": f"SMA Crossover ({fast_period}/{slow_period})",
        "initial_capital": initial_capital,
        "final_capital": round(final_capital, 2),
        "total_return_pct": round(total_return_pct, 2),
        "cagr_pct": round(cagr, 2),
        "buy_and_hold_return_pct": round(bh_return_pct, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "win_rate_pct": round(win_rate, 2),
        "equity_curve": equity_curve,
        "trades": trades[:30],  # Return up to 30 recent trades
        "disclaimer": "Simulated historical performance includes transaction costs and execution slippage. Past results do not guarantee future performance."
    }
