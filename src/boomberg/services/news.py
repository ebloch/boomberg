"""News service for market and company news."""

from datetime import datetime
from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import NewsArticle


class NewsService:
    """Service for fetching news articles."""

    def __init__(self, client: FMPClient):
        self._client = client

    async def get_news(
        self, symbol: Optional[str] = None, limit: int = 50
    ) -> list[NewsArticle]:
        """Get news articles, optionally filtered by symbol."""
        return await self._client.get_news(symbol, limit)

    async def get_market_news(self, limit: int = 50) -> list[NewsArticle]:
        """Get general market news."""
        return await self._client.get_news(limit=limit)

    async def get_symbol_news(self, symbol: str, limit: int = 20) -> list[NewsArticle]:
        """Get news for a specific symbol."""
        return await self._client.get_news(symbol=symbol, limit=limit)

    def format_published_date(self, article: NewsArticle) -> str:
        """Format the published date for display."""
        # FMP API returns UTC times, so use utcnow for comparison
        if article.published_date.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(article.published_date.tzinfo)
        diff = now - article.published_date

        # Handle edge case where article date is slightly in the future
        if diff.total_seconds() < 0:
            return "Just now"

        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago" if minutes > 0 else "Just now"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return article.published_date.strftime("%b %d")

    def truncate_text(self, text: str, max_length: int = 200) -> str:
        """Truncate text to a maximum length with ellipsis."""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3].rsplit(" ", 1)[0] + "..."
