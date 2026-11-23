"""
Virtual Paper Trading Execution and Portfolio Management Engine.
Manages SQLite-persisted holdings, virtual orders, cash balances, and P&L calculations.
STRICT EDUCATIONAL SIMULATION: NEVER CONNECTS TO REAL BROKERS.
"""
import logging
from datetime import datetime, timezone
from config import Config
from backend.database import get_db_connection
from backend.market_data.symbols import normalize_symbol, get_symbol_meta
from backend.market_data.yahoo_provider import market_data_provider

logger = logging.getLogger("quantex.paper_trading")

class PaperTradingEngine:
    def __init__(self):
        self.fee_pct = Config.TRANSACTION_FEE_PCT
        self.slippage_pct = Config.SLIPPAGE_PCT

    def get_portfolio(self) -> dict:
        """
        Retrieves current portfolio state:
        Cash, holdings with mark-to-market valuations, unrealized P&L,
        realized P&L, and asset allocation percentages.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Portfolio cash
        cursor.execute("SELECT cash_balance, initial_balance FROM portfolio WHERE id = 1")
        port_row = cursor.fetchone()
        if not port_row:
            cash = Config.INITIAL_CAPITAL
            initial_balance = Config.INITIAL_CAPITAL
        else:
            cash = float(port_row["cash_balance"])
            initial_balance = float(port_row["initial_balance"])

        # 2. Holdings
        cursor.execute("SELECT symbol, quantity, avg_buy_price FROM holdings WHERE quantity > 0")
        holding_rows = cursor.fetchall()

        holdings = []
        total_holdings_value = 0.0
        total_unrealized_pnl = 0.0

        for row in holding_rows:
            sym = row["symbol"]
            qty = int(row["quantity"])
            avg_price = float(row["avg_buy_price"])

            # Current market quote
            quote = market_data_provider.get_quote(sym)
            curr_price = float(quote.get("price", avg_price))
            invested_val = qty * avg_price
            current_val = qty * curr_price
            pnl = current_val - invested_val
            pnl_pct = (pnl / invested_val * 100) if invested_val > 0 else 0.0

            total_holdings_value += current_val
            total_unrealized_pnl += pnl

            meta = get_symbol_meta(sym)
            holdings.append({
                "symbol": sym,
                "name": meta["name"],
                "quantity": qty,
                "avg_buy_price": round(avg_price, 2),
                "current_price": round(curr_price, 2),
                "invested_amount": round(invested_val, 2),
                "current_value": round(current_val, 2),
                "unrealized_pnl": round(pnl, 2),
                "unrealized_pnl_pct": round(pnl_pct, 2),
                "allocation_pct": 0.0  # calculated below
            })

        # 3. Realized P&L from transactions
        cursor.execute("SELECT SUM(realized_pnl), SUM(fees) FROM transactions")
        txn_stats = cursor.fetchone()
        total_realized_pnl = float(txn_stats[0]) if (txn_stats and txn_stats[0] is not None) else 0.0
        total_fees_paid = float(txn_stats[1]) if (txn_stats and txn_stats[1] is not None) else 0.0
        conn.close()

        total_portfolio_value = cash + total_holdings_value
        overall_pnl = total_portfolio_value - initial_balance
        overall_pnl_pct = (overall_pnl / initial_balance * 100) if initial_balance > 0 else 0.0

        # Calculate allocation percentages
        for h in holdings:
            if total_portfolio_value > 0:
                h["allocation_pct"] = round((h["current_value"] / total_portfolio_value) * 100, 2)

        cash_allocation_pct = round((cash / total_portfolio_value * 100), 2) if total_portfolio_value > 0 else 100.0

        return {
            "initial_capital": round(initial_balance, 2),
            "cash_balance": round(cash, 2),
            "holdings_value": round(total_holdings_value, 2),
            "total_portfolio_value": round(total_portfolio_value, 2),
            "unrealized_pnl": round(total_unrealized_pnl, 2),
            "realized_pnl": round(total_realized_pnl, 2),
            "overall_pnl": round(overall_pnl, 2),
            "overall_pnl_pct": round(overall_pnl_pct, 2),
            "total_fees_paid": round(total_fees_paid, 2),
            "cash_allocation_pct": cash_allocation_pct,
            "holdings_count": len(holdings),
            "holdings": holdings
        }

    def execute_order(self, symbol: str, side: str, quantity: int, notes: str = "") -> dict:
        """
        Validates and executes a virtual paper trading order (BUY or SELL).
        Updates portfolio cash, holdings, and transaction records.
        """
        norm_symbol = normalize_symbol(symbol)
        side = side.strip().upper()

        if side not in ("BUY", "SELL"):
            return {"success": False, "error": "Invalid side. Must be BUY or SELL."}
        if quantity <= 0:
            return {"success": False, "error": "Order quantity must be a positive integer."}

        # Fetch simulated execution price from market data
        quote = market_data_provider.get_quote(norm_symbol)
        base_price = float(quote.get("price", 0.0))
        if base_price <= 0:
            return {"success": False, "error": f"Unable to retrieve market quote for {norm_symbol}."}

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("BEGIN TRANSACTION")

            # Fetch cash
            cursor.execute("SELECT cash_balance FROM portfolio WHERE id = 1")
            cash_row = cursor.fetchone()
            current_cash = float(cash_row["cash_balance"]) if cash_row else Config.INITIAL_CAPITAL

            # Fetch current holding
            cursor.execute("SELECT quantity, avg_buy_price FROM holdings WHERE symbol = ?", (norm_symbol,))
            holding_row = cursor.fetchone()
            current_qty = int(holding_row["quantity"]) if holding_row else 0
            current_avg_price = float(holding_row["avg_buy_price"]) if holding_row else 0.0

            if side == "BUY":
                # Simulated slippage and fee
                exec_price = round(base_price * (1 + self.slippage_pct), 2)
                gross_amount = round(exec_price * quantity, 2)
                fee = round(gross_amount * self.fee_pct, 2)
                total_cost = gross_amount + fee

                if total_cost > current_cash:
                    conn.rollback()
                    conn.close()
                    return {
                        "success": False,
                        "error": f"Insufficient virtual cash. Required: ₹{total_cost:,.2f}, Available: ₹{current_cash:,.2f}."
                    }

                new_cash = current_cash - total_cost
                new_qty = current_qty + quantity
                # Weighted average price
                new_avg_price = ((current_qty * current_avg_price) + (quantity * exec_price)) / new_qty

                # Update portfolio
                cursor.execute("UPDATE portfolio SET cash_balance = ?, updated_at = ? WHERE id = 1",
                               (new_cash, datetime.now(timezone.utc).isoformat()))
                # Update holdings
                cursor.execute("""
                    INSERT INTO holdings (symbol, quantity, avg_buy_price, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(symbol) DO UPDATE SET
                        quantity = excluded.quantity,
                        avg_buy_price = excluded.avg_buy_price,
                        updated_at = excluded.updated_at
                """, (norm_symbol, new_qty, new_avg_price, datetime.now(timezone.utc).isoformat()))

                # Record transaction
                cursor.execute("""
                    INSERT INTO transactions (symbol, side, quantity, price, fees, total_amount, realized_pnl, notes)
                    VALUES (?, 'BUY', ?, ?, ?, ?, 0.0, ?)
                """, (norm_symbol, quantity, exec_price, fee, total_cost, notes or "Virtual Market BUY"))

                realized_pnl = 0.0

            else:  # SELL
                if current_qty < quantity:
                    conn.rollback()
                    conn.close()
                    return {
                        "success": False,
                        "error": f"Insufficient shares to sell. Held: {current_qty}, Requested: {quantity}."
                    }

                exec_price = round(base_price * (1 - self.slippage_pct), 2)
                gross_amount = round(exec_price * quantity, 2)
                fee = round(gross_amount * self.fee_pct, 2)
                net_proceeds = gross_amount - fee

                # Realized P&L
                realized_pnl = round(((exec_price - current_avg_price) * quantity) - fee, 2)
                new_cash = current_cash + net_proceeds
                new_qty = current_qty - quantity

                cursor.execute("UPDATE portfolio SET cash_balance = ?, updated_at = ? WHERE id = 1",
                               (new_cash, datetime.now(timezone.utc).isoformat()))

                if new_qty == 0:
                    cursor.execute("DELETE FROM holdings WHERE symbol = ?", (norm_symbol,))
                else:
                    cursor.execute("UPDATE holdings SET quantity = ?, updated_at = ? WHERE symbol = ?",
                                   (new_qty, datetime.now(timezone.utc).isoformat(), norm_symbol))

                cursor.execute("""
                    INSERT INTO transactions (symbol, side, quantity, price, fees, total_amount, realized_pnl, notes)
                    VALUES (?, 'SELL', ?, ?, ?, ?, ?, ?)
                """, (norm_symbol, quantity, exec_price, fee, net_proceeds, realized_pnl, notes or "Virtual Market SELL"))

            conn.commit()
            conn.close()

            return {
                "success": True,
                "order": {
                    "symbol": norm_symbol,
                    "side": side,
                    "quantity": quantity,
                    "execution_price": exec_price,
                    "fee": fee,
                    "realized_pnl": realized_pnl,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }

        except Exception as e:
            conn.rollback()
            conn.close()
            logger.error(f"Order execution error: {e}")
            return {"success": False, "error": f"Internal execution failure: {str(e)}"}

    def get_transactions(self, limit: int = 50) -> list:
        """Retrieves chronological virtual transaction history."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, timestamp, symbol, side, quantity, price, fees, total_amount, realized_pnl, notes
            FROM transactions
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        conn.close()

        transactions = []
        for r in rows:
            transactions.append({
                "id": r["id"],
                "timestamp": r["timestamp"],
                "symbol": r["symbol"],
                "side": r["side"],
                "quantity": r["quantity"],
                "price": round(r["price"], 2),
                "fees": round(r["fees"], 2),
                "total_amount": round(r["total_amount"], 2),
                "realized_pnl": round(r["realized_pnl"], 2),
                "notes": r["notes"]
            })
        return transactions

paper_trading_engine = PaperTradingEngine()
