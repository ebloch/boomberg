"""Prediction market service for Kalshi markets."""

from typing import Optional

from boomberg.api.exceptions import APIError
from boomberg.api.kalshi_client import KalshiClient
from boomberg.api.kalshi_models import KalshiMarket

# Curated list of economic indicator series from Kalshi
ECONOMIC_SERIES = [
    "KXFED",  # Fed funds rate
    "KXFEDDECISION",  # Fed meeting decisions
    "KXRATECUT",  # Fed rate cuts
    "KXRATECUTCOUNT",  # Number of rate cuts
    "KXCPI",  # Consumer Price Index
    "KXCPICORE",  # Core CPI
    "KXCPIYOY",  # Year-over-year inflation
    "KXU3",  # Unemployment rate
    "KXPAYROLLS",  # Jobs numbers
    "KXGDP",  # US GDP growth
    "KXRECSSNBER",  # Recession
    "KXTNOTE",  # Treasury 10Y yield
    "KX10Y2Y",  # Yield curve spread
]

# Mapping from series ticker to display category
SERIES_CATEGORIES = {
    "KXFED": "Fed Rates",
    "KXFEDDECISION": "Fed Rates",
    "KXRATECUT": "Fed Rates",
    "KXRATECUTCOUNT": "Fed Rates",
    "KXCPI": "Inflation (CPI)",
    "KXCPICORE": "Inflation (CPI)",
    "KXCPIYOY": "Inflation (CPI)",
    "KXU3": "Employment",
    "KXPAYROLLS": "Employment",
    "KXGDP": "GDP",
    "KXRECSSNBER": "Recession",
    "KXTNOTE": "Treasuries",
    "KX10Y2Y": "Treasuries",
}

# Order for displaying categories
CATEGORY_ORDER = [
    "Fed Rates",
    "Inflation (CPI)",
    "Employment",
    "GDP",
    "Recession",
    "Treasuries",
]


class PredictionMarketService:
    """Service for fetching and formatting prediction market data."""

    def __init__(self, client: KalshiClient):
        self._client = client

    async def get_featured_markets(self, limit: int = 15) -> list[KalshiMarket]:
        """Get featured economic markets sorted by 24h volume.

        Fetches markets from curated economic series (Fed rates, CPI, GDP, etc.)
        instead of random events.

        Args:
            limit: Maximum number of markets to return

        Returns:
            List of markets sorted by volume (descending)
        """
        all_markets = []
        for series in ECONOMIC_SERIES:
            try:
                markets = await self._client.get_markets_by_series(series)
                # Set series_ticker on each market
                for market in markets:
                    market.series_ticker = series
                all_markets.extend(markets)
            except APIError:
                continue

        # Dedupe by ticker, keeping first occurrence
        seen: set[str] = set()
        unique_markets = []
        for m in all_markets:
            if m.ticker not in seen:
                seen.add(m.ticker)
                unique_markets.append(m)

        # Sort by 24h volume descending
        sorted_markets = sorted(unique_markets, key=lambda m: m.volume_24h, reverse=True)
        return sorted_markets[:limit]

    async def get_markets_grouped_by_category(self) -> dict[str, list[KalshiMarket]]:
        """Get markets grouped by category name.

        Returns:
            Dictionary mapping category names to lists of markets,
            ordered by CATEGORY_ORDER with markets sorted by volume.
        """
        markets = await self.get_featured_markets(limit=50)

        # Group by category
        grouped: dict[str, list[KalshiMarket]] = {}
        for market in markets:
            if market.series_ticker and market.series_ticker in SERIES_CATEGORIES:
                category = SERIES_CATEGORIES[market.series_ticker]
                if category not in grouped:
                    grouped[category] = []
                grouped[category].append(market)

        # Sort each category's markets by volume
        for category in grouped:
            grouped[category].sort(key=lambda m: m.volume_24h, reverse=True)

        # Return in category order
        ordered: dict[str, list[KalshiMarket]] = {}
        for category in CATEGORY_ORDER:
            if category in grouped:
                ordered[category] = grouped[category]

        return ordered

    async def get_market(self, ticker: str) -> KalshiMarket:
        """Get a single market by ticker."""
        return await self._client.get_market(ticker)

    def format_price_cents(self, cents: Optional[int]) -> str:
        """Format price in cents (e.g., 62 -> '62c')."""
        if cents is None:
            return "-"
        return f"{cents}c"

    def format_change(self, market: KalshiMarket) -> str:
        """Format price change with sign."""
        change = market.change_cents
        if change > 0:
            return f"+{change}c"
        elif change < 0:
            return f"{change}c"
        return "0c"

    def format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        return str(volume)

    def get_change_direction(self, market: KalshiMarket) -> str:
        """Get change direction for styling: 'up', 'down', or 'neutral'."""
        change = market.change_cents
        if change > 0:
            return "up"
        elif change < 0:
            return "down"
        return "neutral"

    def truncate_title(self, title: str, max_length: int = 45) -> str:
        """Truncate title to max length with ellipsis."""
        if len(title) <= max_length:
            return title
        return title[: max_length - 3] + "..."
