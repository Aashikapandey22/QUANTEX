"""
QUANTEX Configuration Module
Manages application settings, database paths, market data configuration, and AI models.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
MODELS_DIR = BASE_DIR / "models"
MODELS_DIR.mkdir(exist_ok=True)

class Config:
    # App Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "quantex-institutional-secret-key-2026")
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    
    # Database Settings
    DATABASE_PATH = str(DATA_DIR / "quantex.db")
    
    # Virtual Paper Trading
    INITIAL_CAPITAL = float(os.getenv("INITIAL_CAPITAL", "1000000.0"))  # INR 10,00,000
    TRANSACTION_FEE_PCT = float(os.getenv("TRANSACTION_FEE_PCT", "0.001"))  # 0.1% brokerage/slippage simulation
    SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.0005"))  # 0.05% execution slippage
    
    # Market Data
    CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "300"))  # 5 min cache
    DEFAULT_WATCHLIST = [
        "RELIANCE.NS",
        "TCS.NS",
        "INFY.NS",
        "HDFCBANK.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "ITC.NS",
        "LT.NS",
        "TATAMOTORS.NS",
        "BHARTIARTL.NS"
    ]
    
    # Google Gemini AI Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # ML Pipeline Settings
    DEFAULT_HORIZON_DAYS = 5
    ML_MODELS = ["logistic_regression", "random_forest"]
