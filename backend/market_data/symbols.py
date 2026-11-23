"""
Indian Equities Watchlist and Metadata Registry.
Supports National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) mappings.
Enforces strict symbol validation against verified financial instruments
to prevent arbitrary English words from being converted into fictitious tickers.
"""

# Explicit list of common English words that must NEVER be treated as stock tickers
COMMON_ENGLISH_WORDS = {
    "SHOULD", "WOULD", "COULD", "MIGHT", "MUST", "SHALL",
    "BUY", "SELL", "HOLD", "INVEST", "INVESTING", "TRADE", "TRADING",
    "CAN", "WILL", "THE", "THIS", "THAT", "WHAT", "WHEN", "WHERE", "WHICH", "WHY", "HOW",
    "GOOD", "BAD", "TIME", "DAY", "DAYS", "MARKET", "STOCK", "STOCKS", "SHARE", "SHARES", "EQUITY", "PRICE",
    "PREDICT", "PREDICTION", "ANALYSE", "ANALYZE", "ANALYSIS", "EXPLAIN", "COMPARE", "COMPARISON",
    "SHOW", "VIEW", "GET", "DISPLAY", "FIND", "SEARCH", "CHECK", "TEST",
    "PORTFOLIO", "RISK", "BACKTEST", "STRATEGY", "ORDERS", "TRANSACTIONS",
    "MOVING", "AVERAGE", "PAPER", "TRADING", "TRADED", "TRADER",
    "TODAY", "TOMORROW", "YESTERDAY", "NOW", "SOON", "LATER",
    "FOR", "AND", "WITH", "ABOUT", "THINK", "YOU", "YOUR", "OUR", "THEIR",
    "DOES", "DOESN'T", "DONT", "PLEASE", "HELP", "HELLO", "HI", "HEY",
    "YES", "NO", "MAYBE", "OK", "SURE", "THANKS", "THANK", "SO", "MY", "ME", "ALL"
}

WATCHLIST_METADATA = {
    "RELIANCE.NS": {
        "symbol": "RELIANCE.NS",
        "ticker": "RELIANCE",
        "name": "Reliance Industries Limited",
        "sector": "Energy & Conglomerate",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 2980.50,
        "lot_size": 1
    },
    "TCS.NS": {
        "symbol": "TCS.NS",
        "ticker": "TCS",
        "name": "Tata Consultancy Services Ltd",
        "sector": "Information Technology",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 4120.00,
        "lot_size": 1
    },
    "INFY.NS": {
        "symbol": "INFY.NS",
        "ticker": "INFY",
        "name": "Infosys Limited",
        "sector": "Information Technology",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 1845.20,
        "lot_size": 1
    },
    "HDFCBANK.NS": {
        "symbol": "HDFCBANK.NS",
        "ticker": "HDFCBANK",
        "name": "HDFC Bank Limited",
        "sector": "Banking & Financials",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 1670.30,
        "lot_size": 1
    },
    "ICICIBANK.NS": {
        "symbol": "ICICIBANK.NS",
        "ticker": "ICICIBANK",
        "name": "ICICI Bank Limited",
        "sector": "Banking & Financials",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 1240.75,
        "lot_size": 1
    },
    "SBIN.NS": {
        "symbol": "SBIN.NS",
        "ticker": "SBIN",
        "name": "State Bank of India",
        "sector": "Public Sector Banking",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 820.60,
        "lot_size": 1
    },
    "ITC.NS": {
        "symbol": "ITC.NS",
        "ticker": "ITC",
        "name": "ITC Limited",
        "sector": "Consumer Goods (FMCG)",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 490.40,
        "lot_size": 1
    },
    "LT.NS": {
        "symbol": "LT.NS",
        "ticker": "LT",
        "name": "Larsen & Toubro Limited",
        "sector": "Infrastructure & Engineering",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 3610.00,
        "lot_size": 1
    },
    "TATAMOTORS.NS": {
        "symbol": "TATAMOTORS.NS",
        "ticker": "TATAMOTORS",
        "name": "Tata Motors Limited",
        "sector": "Automobile",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 995.80,
        "lot_size": 1
    },
    "BHARTIARTL.NS": {
        "symbol": "BHARTIARTL.NS",
        "ticker": "BHARTIARTL",
        "name": "Bharti Airtel Limited",
        "sector": "Telecommunications",
        "exchange": "NSE",
        "currency": "INR",
        "benchmark_price": 1585.10,
        "lot_size": 1
    }
}

# Lookup map of bare tickers to canonical .NS symbol
TICKER_TO_SYMBOL = {
    meta["ticker"]: sym for sym, meta in WATCHLIST_METADATA.items()
}

def is_valid_symbol(symbol: str) -> bool:
    """
    Validates whether a symbol string corresponds to a verified Indian equity instrument.
    Rejects ordinary words, empty strings, and unsupported tickers.
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    clean = symbol.strip().upper()
    if clean in COMMON_ENGLISH_WORDS:
        return False

    # Check direct canonical match
    if clean in WATCHLIST_METADATA:
        return True

    # Strip .NS or .BO suffix if present
    base = clean
    if clean.endswith(".NS") or clean.endswith(".BO"):
        base = clean[:-3]

    if base in COMMON_ENGLISH_WORDS:
        return False

    return base in TICKER_TO_SYMBOL

def safe_normalize_symbol(symbol: str) -> str | None:
    """
    Safely normalizes a symbol string to canonical format (e.g. 'TCS' -> 'TCS.NS').
    Returns None if the symbol is not in the verified instrument registry.
    NEVER appends .NS to arbitrary English words.
    """
    if not symbol or not isinstance(symbol, str):
        return None
    
    clean = symbol.strip().upper()
    if clean in COMMON_ENGLISH_WORDS:
        return None

    if clean in WATCHLIST_METADATA:
        return clean

    base = clean[:-3] if (clean.endswith(".NS") or clean.endswith(".BO")) else clean
    if base in TICKER_TO_SYMBOL:
        return TICKER_TO_SYMBOL[base]

    return None

def normalize_symbol(symbol: str) -> str:
    """
    Normalizes symbol string to canonical format.
    Raises ValueError if symbol is not a valid registered instrument.
    """
    norm = safe_normalize_symbol(symbol)
    if not norm:
        raise ValueError(f"Invalid or unsupported stock symbol: '{symbol}'. Please select a verified Indian equity.")
    return norm

def get_symbol_meta(symbol: str) -> dict:
    """
    Retrieves corporate metadata for a verified instrument.
    Raises ValueError if the symbol is unrecognized.
    """
    norm = safe_normalize_symbol(symbol)
    if not norm or norm not in WATCHLIST_METADATA:
        raise ValueError(f"Unknown instrument '{symbol}'. Symbol must be a verified Indian equity.")
    return WATCHLIST_METADATA[norm]
