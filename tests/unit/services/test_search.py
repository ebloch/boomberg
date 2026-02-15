"""Unit tests for SearchService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import SearchResult
from boomberg.services.search import SearchService


class TestSearchService:
    """Tests for SearchService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create SearchService with mock client."""
        return SearchService(mock_client)

    @pytest.fixture
    def sample_results(self) -> list[SearchResult]:
        """Create sample search results."""
        return [
            SearchResult(
                symbol="AAPL",
                name="Apple Inc.",
                currency="USD",
                exchange="NASDAQ",
                exchange_full="NASDAQ Global Select",
            ),
            SearchResult(
                symbol="APC.F",
                name="Apple Inc.",
                currency="EUR",
                exchange="FSX",
                exchange_full="Frankfurt Stock Exchange",
            ),
        ]

    @pytest.mark.asyncio
    async def test_search(self, service, mock_client, sample_results):
        """Test searching for symbols."""
        mock_client.search = AsyncMock(return_value=sample_results)

        result = await service.search("apple", limit=10)

        assert len(result) == 2
        mock_client.search.assert_called_once_with("apple", 10)

    @pytest.mark.asyncio
    async def test_search_empty(self, service, mock_client):
        """Test search with no results."""
        mock_client.search = AsyncMock(return_value=[])

        result = await service.search("xyznonexistent")

        assert result == []

    def test_format_result(self, service, sample_results):
        """Test formatting search result."""
        result = service.format_result(sample_results[0])
        assert result == "AAPL - Apple Inc. (NASDAQ)"

    def test_highlight_match(self, service):
        """Test highlighting matching text."""
        result = service.highlight_match("Apple Inc.", "apple")
        assert "[bold yellow]Apple[/bold yellow]" in result
        assert "Inc." in result

    def test_highlight_match_no_match(self, service):
        """Test highlighting with no match."""
        result = service.highlight_match("Microsoft Corp", "apple")
        assert result == "Microsoft Corp"

    def test_highlight_match_case_insensitive(self, service):
        """Test highlighting is case insensitive."""
        result = service.highlight_match("APPLE Inc.", "apple")
        assert "[bold yellow]APPLE[/bold yellow]" in result
