"""Quote service for real-time stock quotes."""

from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import Quote


class QuoteService:
    """Service for fetching real-time stock quotes."""

    def __init__(self, client: FMPClient):
        self._client = client

    async def get_quote(self, symbol: str) -> Quote:
        """Get a single quote for a symbol."""
        return await self._client.get_quote(symbol)

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for multiple symbols."""
        return await self._client.get_quotes(symbols)

    def format_change(self, quote: Quote) -> str:
        """Format the change value with sign and percentage."""
        sign = "+" if quote.change >= 0 else ""
        return f"{sign}{quote.change:.2f} ({sign}{quote.change_percent:.2f}%)"

    def get_change_direction(self, quote: Quote) -> str:
        """Get change direction for styling: 'up', 'down', or 'neutral'."""
        if quote.change > 0:
            return "up"
        elif quote.change < 0:
            return "down"
        return "neutral"

    def format_market_cap(self, market_cap: Optional[float]) -> str:
        """Format market cap in human-readable form."""
        if market_cap is None:
            return "N/A"
        if market_cap >= 1e12:
            return f"${market_cap / 1e12:.2f}T"
        if market_cap >= 1e9:
            return f"${market_cap / 1e9:.2f}B"
        if market_cap >= 1e6:
            return f"${market_cap / 1e6:.2f}M"
        return f"${market_cap:,.0f}"

    def format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1e9:
            return f"{volume / 1e9:.2f}B"
        if volume >= 1e6:
            return f"{volume / 1e6:.2f}M"
        if volume >= 1e3:
            return f"{volume / 1e3:.2f}K"
        return f"{volume:,}"
