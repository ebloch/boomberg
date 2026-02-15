"""Historical data service."""

from datetime import date
from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import HistoricalPrice


class HistoricalService:
    """Service for fetching historical price data."""

    VALID_PERIODS = ["1D", "1W", "1M", "3M", "6M", "1Y", "5Y"]

    def __init__(self, client: FMPClient):
        self._client = client

    async def get_historical_prices(
        self,
        symbol: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[HistoricalPrice]:
        """Get historical prices for a date range."""
        return await self._client.get_historical_prices(symbol, from_date, to_date)

    async def get_historical_prices_period(
        self, symbol: str, period: str = "1M"
    ) -> list[HistoricalPrice]:
        """Get historical prices for a predefined period."""
        period = period.upper()
        if period not in self.VALID_PERIODS:
            raise ValueError(f"Invalid period: {period}. Valid: {self.VALID_PERIODS}")
        return await self._client.get_historical_prices_period(symbol, period)

    def calculate_returns(self, prices: list[HistoricalPrice]) -> Optional[float]:
        """Calculate percentage return over the price period."""
        if len(prices) < 2:
            return None
        # Prices are typically newest first
        newest = prices[0].close
        oldest = prices[-1].close
        if oldest == 0:
            return None
        return ((newest - oldest) / oldest) * 100

    def get_price_range(
        self, prices: list[HistoricalPrice]
    ) -> tuple[float, float] | None:
        """Get high and low over the price period."""
        if not prices:
            return None
        high = max(p.high for p in prices)
        low = min(p.low for p in prices)
        return (low, high)

    def get_average_volume(self, prices: list[HistoricalPrice]) -> Optional[float]:
        """Calculate average volume over the period."""
        if not prices:
            return None
        return sum(p.volume for p in prices) / len(prices)
