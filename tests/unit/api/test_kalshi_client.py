"""Unit tests for Kalshi API client."""

import pytest
import respx
from httpx import Response

from boomberg.api.kalshi_client import KalshiClient
from boomberg.api.kalshi_models import KalshiMarket
from boomberg.api.exceptions import APIError


@pytest.fixture
def sample_kalshi_market_data() -> dict:
    """Sample Kalshi market API response data."""
    return {
        "ticker": "FED-25MAR-T4.75",
        "title": "Will the Fed cut rates in March 2025?",
        "yes_bid": 62,
        "no_bid": 36,
        "yes_ask": 64,
        "no_ask": 38,
        "last_price": 63,
        "previous_price": 60,
        "volume_24h": 125400,
        "open_interest": 450200,
        "status": "active",
        "close_time": "2025-03-15T16:00:00Z",
    }


@pytest.fixture
def sample_kalshi_markets_response(sample_kalshi_market_data) -> dict:
    """Sample Kalshi markets list API response."""
    return {
        "markets": [
            sample_kalshi_market_data,
            {
                "ticker": "BTC-100K-EOY",
                "title": "Will BTC hit $100K by EOY?",
                "yes_bid": 45,
                "no_bid": 53,
                "yes_ask": 47,
                "no_ask": 55,
                "last_price": 45,
                "previous_price": 47,
                "volume_24h": 89200,
                "open_interest": 320000,
                "status": "active",
                "close_time": "2025-12-31T23:59:59Z",
            },
        ],
        "cursor": None,
    }


@pytest.fixture
def sample_events_response() -> dict:
    """Sample events list API response."""
    return {
        "events": [
            {"event_ticker": "KXFED-25MAR", "title": "Fed March 2025"},
            {"event_ticker": "KXBTC-100K", "title": "BTC 100K"},
        ]
    }


class TestKalshiClient:
    """Tests for KalshiClient."""

    @pytest.fixture
    def client(self):
        """Create Kalshi client."""
        return KalshiClient()

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_markets_success(
        self, client, sample_events_response, sample_kalshi_markets_response
    ):
        """Test successful markets retrieval via events."""
        # Mock events endpoint
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/events"
        ).mock(return_value=Response(200, json=sample_events_response))

        # Mock markets endpoint for each event
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params__contains={"event_ticker": "KXFED-25MAR"},
        ).mock(return_value=Response(200, json=sample_kalshi_markets_response))

        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params__contains={"event_ticker": "KXBTC-100K"},
        ).mock(return_value=Response(200, json={"markets": []}))

        async with client:
            markets = await client.get_markets(limit=10)

        assert len(markets) == 2
        assert all(isinstance(m, KalshiMarket) for m in markets)
        assert markets[0].ticker == "FED-25MAR-T4.75"
        assert markets[1].ticker == "BTC-100K-EOY"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_markets_for_event(self, client, sample_kalshi_markets_response):
        """Test fetching markets for a specific event."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params__contains={"event_ticker": "KXFED-25MAR"},
        ).mock(return_value=Response(200, json=sample_kalshi_markets_response))

        async with client:
            markets = await client.get_markets_for_event("KXFED-25MAR")

        assert len(markets) == 2
        assert all(isinstance(m, KalshiMarket) for m in markets)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_events(self, client, sample_events_response):
        """Test fetching events."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/events"
        ).mock(return_value=Response(200, json=sample_events_response))

        async with client:
            events = await client.get_events(limit=10)

        assert len(events) == 2
        assert events[0]["event_ticker"] == "KXFED-25MAR"

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_market_by_ticker_success(self, client, sample_kalshi_market_data):
        """Test successful single market retrieval."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets/FED-25MAR-T4.75"
        ).mock(return_value=Response(200, json={"market": sample_kalshi_market_data}))

        async with client:
            market = await client.get_market("FED-25MAR-T4.75")

        assert isinstance(market, KalshiMarket)
        assert market.ticker == "FED-25MAR-T4.75"
        assert market.title == "Will the Fed cut rates in March 2025?"
        assert market.yes_bid == 62

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_market_not_found(self, client):
        """Test market retrieval for unknown ticker."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets/INVALID"
        ).mock(return_value=Response(404, json={"error": "Market not found"}))

        async with client:
            with pytest.raises(APIError) as exc_info:
                await client.get_market("INVALID")

        assert exc_info.value.status_code == 404

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_markets_empty_events(self, client):
        """Test empty events response."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/events"
        ).mock(return_value=Response(200, json={"events": []}))

        async with client:
            markets = await client.get_markets()

        assert markets == []

    @pytest.mark.asyncio
    async def test_client_context_manager(self, client):
        """Test client async context manager."""
        assert client._client is None

        async with client:
            assert client._client is not None

        assert client._client is None

    def test_client_not_initialized_error(self, client):
        """Test error when accessing client before initialization."""
        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_markets_by_series(self, client, sample_kalshi_markets_response):
        """Test fetching markets for a specific series."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params__contains={"series_ticker": "KXFED"},
        ).mock(return_value=Response(200, json=sample_kalshi_markets_response))

        async with client:
            markets = await client.get_markets_by_series("KXFED")

        assert len(markets) == 2
        assert all(isinstance(m, KalshiMarket) for m in markets)

    @respx.mock
    @pytest.mark.asyncio
    async def test_get_markets_by_series_empty(self, client):
        """Test fetching markets for a series with no markets."""
        respx.get(
            "https://api.elections.kalshi.com/trade-api/v2/markets",
            params__contains={"series_ticker": "KXEMPTY"},
        ).mock(return_value=Response(200, json={"markets": []}))

        async with client:
            markets = await client.get_markets_by_series("KXEMPTY")

        assert markets == []
