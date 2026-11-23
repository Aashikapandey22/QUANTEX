"""
Database management module for QUANTEX.
Handles SQLite connection, schema initialization, and transactional persistence.
"""
import sqlite3
import json
from datetime import datetime, timezone
from config import Config

def get_db_connection(db_path=None):
    """Returns a sqlite3 connection with dict-like row factory."""
    path = db_path or Config.DATABASE_PATH
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    """Initializes the database schema if tables do not exist."""
    path = db_path or Config.DATABASE_PATH
    conn = get_db_connection(path)
    cursor = conn.cursor()

    # Portfolio table (single record id=1)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        cash_balance REAL NOT NULL,
        initial_balance REAL NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Holdings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holdings (
        symbol TEXT PRIMARY KEY,
        quantity INTEGER NOT NULL,
        avg_buy_price REAL NOT NULL,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        symbol TEXT NOT NULL,
        side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
        quantity INTEGER NOT NULL,
        price REAL NOT NULL,
        fees REAL NOT NULL,
        total_amount REAL NOT NULL,
        realized_pnl REAL DEFAULT 0.0,
        notes TEXT
    );
    """)

    # Market data cache table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS market_cache (
        cache_key TEXT PRIMARY KEY,
        symbol TEXT NOT NULL,
        period TEXT NOT NULL,
        data_json TEXT NOT NULL,
        timestamp REAL NOT NULL
    );
    """)

    # AI Agent logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS agent_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        user_query TEXT NOT NULL,
        plan_steps TEXT NOT NULL,
        tools_called TEXT NOT NULL,
        observation TEXT NOT NULL,
        status TEXT NOT NULL
    );
    """)

    # Initialize default portfolio if not present
    cursor.execute("SELECT id FROM portfolio WHERE id = 1")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO portfolio (id, cash_balance, initial_balance, updated_at) VALUES (1, ?, ?, ?)",
            (Config.INITIAL_CAPITAL, Config.INITIAL_CAPITAL, datetime.now(timezone.utc).isoformat())
        )

    conn.commit()
    conn.close()

def reset_db(db_path=None):
    """Resets portfolio and paper trading tables for clean state/testing."""
    path = db_path or Config.DATABASE_PATH
    conn = get_db_connection(path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM holdings")
    cursor.execute("DELETE FROM transactions")
    cursor.execute("DELETE FROM portfolio")
    cursor.execute("DELETE FROM agent_logs")
    cursor.execute(
        "INSERT INTO portfolio (id, cash_balance, initial_balance, updated_at) VALUES (1, ?, ?, ?)",
        (Config.INITIAL_CAPITAL, Config.INITIAL_CAPITAL, datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()
