"""Unit tests for FMP API client."""

import pytest
import respx
from httpx import Response

from boomberg.api.client import FMPClient
from boomberg.api.exceptions import APIError, RateLimitError, SymbolNotFoundError
from boomberg.api.models import (
    CompanyProfile,
    HistoricalPrice,
    NewsArticle,
    Quote,
    SearchResult,
)


class TestFMPClient:
    """Tests for FMPClient."""

    @pytest.fixture
    def client(self, test_settings):
        """Create FMP client with test settings."""
        return FMPClient(settings=test_settings)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_quote_success(self, client, sample_quote_data):
        """Test successful quote retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/quote"
        ).mock(return_value=Response(200, json=[sample_quote_data]))

        async with client:
            quote = await client.get_quote("AAPL")

        assert isinstance(quote, Quote)
        assert quote.symbol == "AAPL"
        assert quote.price == 185.50
        assert quote.change == 2.35
        assert quote.change_percent == 1.28

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_quote_symbol_not_found(self, client):
        """Test quote retrieval for unknown symbol."""
        respx.get(
            "https://financialmodelingprep.com/stable/quote"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            with pytest.raises(SymbolNotFoundError) as exc_info:
                await client.get_quote("INVALID")

        assert exc_info.value.symbol == "INVALID"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_quote_rate_limit(self, client):
        """Test rate limit handling."""
        respx.get(
            "https://financialmodelingprep.com/stable/quote"
        ).mock(return_value=Response(429, json={"error": "Rate limit exceeded"}))

        async with client:
            with pytest.raises(RateLimitError):
                await client.get_quote("AAPL")

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_quotes_multiple(self, client, sample_quote_data):
        """Test batch quote retrieval."""
        msft_data = {**sample_quote_data, "symbol": "MSFT", "price": 405.00}
        # Mock individual quote endpoints since stable API doesn't support batch
        respx.get(
            "https://financialmodelingprep.com/stable/quote",
            params__contains={"symbol": "AAPL"}
        ).mock(return_value=Response(200, json=[sample_quote_data]))
        respx.get(
            "https://financialmodelingprep.com/stable/quote",
            params__contains={"symbol": "MSFT"}
        ).mock(return_value=Response(200, json=[msft_data]))

        async with client:
            quotes = await client.get_quotes(["AAPL", "MSFT"])

        assert len(quotes) == 2
        symbols = {q.symbol for q in quotes}
        assert symbols == {"AAPL", "MSFT"}

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_quotes_empty_list(self, client):
        """Test batch quote with empty list."""
        async with client:
            quotes = await client.get_quotes([])

        assert quotes == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_historical_prices(self, client, sample_historical_data):
        """Test historical price retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/historical-price-eod/full"
        ).mock(return_value=Response(200, json=sample_historical_data))

        async with client:
            prices = await client.get_historical_prices("AAPL")

        assert len(prices) == 2
        assert all(isinstance(p, HistoricalPrice) for p in prices)
        assert prices[0].close == 184.50

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_historical_prices_empty(self, client):
        """Test historical price retrieval with no data."""
        respx.get(
            "https://financialmodelingprep.com/stable/historical-price-eod/full"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            prices = await client.get_historical_prices("INVALID")

        assert prices == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_company_profile(self, client, sample_profile_data):
        """Test company profile retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/profile"
        ).mock(return_value=Response(200, json=[sample_profile_data]))

        async with client:
            profile = await client.get_company_profile("AAPL")

        assert isinstance(profile, CompanyProfile)
        assert profile.symbol == "AAPL"
        assert profile.company_name == "Apple Inc."
        assert profile.sector == "Technology"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_company_profile_not_found(self, client):
        """Test company profile for unknown symbol."""
        respx.get(
            "https://financialmodelingprep.com/stable/profile"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            with pytest.raises(SymbolNotFoundError):
                await client.get_company_profile("INVALID")

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_news(self, client, sample_news_data):
        """Test news retrieval."""
        respx.get(
            "https://financialmodelingprep.com/stable/news/stock"
        ).mock(return_value=Response(200, json=sample_news_data))

        async with client:
            news = await client.get_news(symbol="AAPL", limit=10)

        assert len(news) == 1
        assert isinstance(news[0], NewsArticle)
        assert news[0].title == "Apple Reports Record Q4 Earnings"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_news_empty(self, client):
        """Test news retrieval with no results."""
        respx.get(
            "https://financialmodelingprep.com/stable/news/stock-latest"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            news = await client.get_news()

        assert news == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_search(self, client, sample_search_data):
        """Test symbol search."""
        respx.get(
            "https://financialmodelingprep.com/stable/search-name"
        ).mock(return_value=Response(200, json=sample_search_data))

        async with client:
            results = await client.search("apple", limit=10)

        assert len(results) == 2
        assert all(isinstance(r, SearchResult) for r in results)
        assert results[0].symbol == "AAPL"

    @respx.mock
    @pytest.mark.asyncio
    async def test_search_empty(self, client):
        """Test symbol search with no results."""
        respx.get(
            "https://financialmodelingprep.com/stable/search-name"
        ).mock(return_value=Response(200, json=[]))

        async with client:
            results = await client.search("xyznonexistent")

        assert results == []

    @respx.mock
    @pytest.mark.asyncio
    async def test_api_error_handling(self, client):
        """Test general API error handling."""
        respx.get(
            "https://financialmodelingprep.com/stable/quote"
        ).mock(return_value=Response(500, text="Internal Server Error"))

        async with client:
            with pytest.raises(APIError) as exc_info:
                await client.get_quote("AAPL")

        assert exc_info.value.status_code == 500

    def test_client_not_initialized(self, client):
        """Test error when client used without context manager."""
        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client
