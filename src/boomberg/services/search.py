"""Search service for symbol lookup."""

from boomberg.api.client import FMPClient
from boomberg.api.models import SearchResult


class SearchService:
    """Service for searching symbols."""

    def __init__(self, client: FMPClient):
        self._client = client

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for symbols by name or ticker."""
        return await self._client.search(query, limit)

    def format_result(self, result: SearchResult) -> str:
        """Format a search result for display."""
        return f"{result.symbol} - {result.name} ({result.exchange})"

    def highlight_match(self, text: str, query: str) -> str:
        """Highlight matching query in text (returns Rich markup)."""
        query_lower = query.lower()
        text_lower = text.lower()

        if query_lower not in text_lower:
            return text

        idx = text_lower.index(query_lower)
        before = text[:idx]
        match = text[idx : idx + len(query)]
        after = text[idx + len(query) :]

        return f"{before}[bold yellow]{match}[/bold yellow]{after}"
