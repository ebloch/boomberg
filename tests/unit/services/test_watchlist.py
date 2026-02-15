"""Unit tests for WatchlistService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import Quote
from boomberg.services.watchlist import WatchlistService


class TestWatchlistService:
    """Tests for WatchlistService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def mock_store(self):
        """Create a mock watchlist store."""
        store = MagicMock()
        store.load.return_value = {"default": ["AAPL", "MSFT"]}
        return store

    @pytest.fixture
    def service(self, mock_client, mock_store):
        """Create WatchlistService with mock dependencies."""
        return WatchlistService(mock_client, mock_store)

    @pytest.mark.asyncio
    async def test_get_watchlists(self, service):
        """Test getting all watchlists."""
        result = await service.get_watchlists()
        assert "default" in result
        assert result["default"] == ["AAPL", "MSFT"]

    @pytest.mark.asyncio
    async def test_get_watchlist(self, service):
        """Test getting a specific watchlist."""
        result = await service.get_watchlist("default")
        assert result == ["AAPL", "MSFT"]

    @pytest.mark.asyncio
    async def test_get_watchlist_not_found(self, service):
        """Test getting a non-existent watchlist."""
        result = await service.get_watchlist("nonexistent")
        assert result == []

    @pytest.mark.asyncio
    async def test_create_watchlist(self, service, mock_store):
        """Test creating a new watchlist."""
        await service.create_watchlist("tech")

        watchlists = await service.get_watchlists()
        assert "tech" in watchlists
        mock_store.save.assert_called()

    @pytest.mark.asyncio
    async def test_create_watchlist_already_exists(self, service, mock_store):
        """Test creating a watchlist that already exists."""
        # First call loads existing watchlists
        await service.get_watchlists()
        mock_store.save.reset_mock()

        await service.create_watchlist("default")
        # Should not save if watchlist already exists
        mock_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_watchlist(self, service, mock_store):
        """Test deleting a watchlist."""
        await service.create_watchlist("temp")
        result = await service.delete_watchlist("temp")

        assert result is True
        mock_store.save.assert_called()

    @pytest.mark.asyncio
    async def test_delete_watchlist_not_found(self, service):
        """Test deleting a non-existent watchlist."""
        result = await service.delete_watchlist("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_add_symbol(self, service, mock_store):
        """Test adding a symbol to watchlist."""
        result = await service.add_symbol("GOOGL", "default")

        assert result is True
        watchlist = await service.get_watchlist("default")
        assert "GOOGL" in watchlist
        mock_store.save.assert_called()

    @pytest.mark.asyncio
    async def test_add_symbol_already_exists(self, service, mock_store):
        """Test adding a symbol that already exists."""
        mock_store.save.reset_mock()
        result = await service.add_symbol("AAPL", "default")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_symbol_uppercase(self, service):
        """Test that symbols are normalized to uppercase."""
        await service.add_symbol("googl", "default")
        watchlist = await service.get_watchlist("default")
        assert "GOOGL" in watchlist

    @pytest.mark.asyncio
    async def test_add_symbol_creates_watchlist(self, service):
        """Test adding symbol to non-existent watchlist creates it."""
        await service.add_symbol("TSLA", "new_list")
        watchlist = await service.get_watchlist("new_list")
        assert "TSLA" in watchlist

    @pytest.mark.asyncio
    async def test_remove_symbol(self, service, mock_store):
        """Test removing a symbol from watchlist."""
        result = await service.remove_symbol("AAPL", "default")

        assert result is True
        watchlist = await service.get_watchlist("default")
        assert "AAPL" not in watchlist
        mock_store.save.assert_called()

    @pytest.mark.asyncio
    async def test_remove_symbol_not_found(self, service):
        """Test removing a symbol that doesn't exist."""
        result = await service.remove_symbol("TSLA", "default")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_watchlist_quotes(self, service, mock_client):
        """Test getting quotes for watchlist symbols."""
        quotes = [
            Quote(symbol="AAPL", name="Apple", price=185.0),
            Quote(symbol="MSFT", name="Microsoft", price=405.0),
        ]
        mock_client.get_quotes = AsyncMock(return_value=quotes)

        result = await service.get_watchlist_quotes("default")

        assert len(result) == 2
        mock_client.get_quotes.assert_called_once_with(["AAPL", "MSFT"])

    @pytest.mark.asyncio
    async def test_get_watchlist_quotes_empty(self, service, mock_client, mock_store):
        """Test getting quotes for empty watchlist."""
        mock_store.load.return_value = {"default": []}
        service = WatchlistService(mock_client, mock_store)

        result = await service.get_watchlist_quotes("default")

        assert result == []

    @pytest.mark.asyncio
    async def test_symbol_exists(self, service):
        """Test checking if symbol exists in watchlist."""
        assert await service.symbol_exists("AAPL") is True
        assert await service.symbol_exists("TSLA") is False

    @pytest.mark.asyncio
    async def test_symbol_exists_case_insensitive(self, service):
        """Test symbol existence check is case insensitive."""
        assert await service.symbol_exists("aapl") is True
