"""
Abstract Market Data Provider Interface.
Allows plugging in alternate data sources (e.g. AlphaVantage, Kite Connect, etc.) in the future.
"""
from abc import ABC, abstractmethod
import pandas as pd

class MarketDataProvider(ABC):
    @abstractmethod
    def get_quote(self, symbol: str) -> dict:
        """Fetch current / latest quote snapshot."""
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, period: str = "1Y") -> pd.DataFrame:
        """Fetch OHLCV historical dataframe."""
        pass

    @abstractmethod
    def get_watchlist_overview(self) -> list:
        """Fetch quotes for all watchlist symbols."""
        pass
