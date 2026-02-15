"""Unit tests for QuoteService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import Quote
from boomberg.services.quotes import QuoteService


class TestQuoteService:
    """Tests for QuoteService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create QuoteService with mock client."""
        return QuoteService(mock_client)

    @pytest.fixture
    def sample_quote(self) -> Quote:
        """Create a sample quote."""
        return Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=185.50,
            change=2.35,
            change_percent=1.28,
            day_low=183.00,
            day_high=186.50,
            market_cap=2890000000000,
            volume=52500000,
        )

    @pytest.mark.asyncio
    async def test_get_quote(self, service, mock_client, sample_quote):
        """Test fetching a single quote."""
        mock_client.get_quote = AsyncMock(return_value=sample_quote)

        result = await service.get_quote("AAPL")

        assert result == sample_quote
        mock_client.get_quote.assert_called_once_with("AAPL")

    @pytest.mark.asyncio
    async def test_get_quotes_multiple(self, service, mock_client, sample_quote):
        """Test fetching multiple quotes."""
        msft_quote = Quote(
            symbol="MSFT", name="Microsoft Corp", price=405.00, change=-1.50
        )
        mock_client.get_quotes = AsyncMock(return_value=[sample_quote, msft_quote])

        result = await service.get_quotes(["AAPL", "MSFT"])

        assert len(result) == 2
        mock_client.get_quotes.assert_called_once_with(["AAPL", "MSFT"])

    def test_format_change_positive(self, service, sample_quote):
        """Test formatting positive change."""
        result = service.format_change(sample_quote)
        assert result == "+2.35 (+1.28%)"

    def test_format_change_negative(self, service):
        """Test formatting negative change."""
        quote = Quote(symbol="MSFT", price=405.00, change=-1.50, change_percent=-0.37)
        result = service.format_change(quote)
        assert result == "-1.50 (-0.37%)"

    def test_get_change_direction_up(self, service, sample_quote):
        """Test change direction for positive change."""
        assert service.get_change_direction(sample_quote) == "up"

    def test_get_change_direction_down(self, service):
        """Test change direction for negative change."""
        quote = Quote(symbol="MSFT", price=405.00, change=-1.50)
        assert service.get_change_direction(quote) == "down"

    def test_get_change_direction_neutral(self, service):
        """Test change direction for zero change."""
        quote = Quote(symbol="MSFT", price=405.00, change=0.0)
        assert service.get_change_direction(quote) == "neutral"

    def test_format_market_cap_trillion(self, service):
        """Test market cap formatting for trillions."""
        assert service.format_market_cap(2890000000000) == "$2.89T"

    def test_format_market_cap_billion(self, service):
        """Test market cap formatting for billions."""
        assert service.format_market_cap(150000000000) == "$150.00B"

    def test_format_market_cap_million(self, service):
        """Test market cap formatting for millions."""
        assert service.format_market_cap(500000000) == "$500.00M"

    def test_format_market_cap_small(self, service):
        """Test market cap formatting for smaller values."""
        assert service.format_market_cap(50000) == "$50,000"

    def test_format_market_cap_none(self, service):
        """Test market cap formatting for None."""
        assert service.format_market_cap(None) == "N/A"

    def test_format_volume_billion(self, service):
        """Test volume formatting for billions."""
        assert service.format_volume(1500000000) == "1.50B"

    def test_format_volume_million(self, service):
        """Test volume formatting for millions."""
        assert service.format_volume(52500000) == "52.50M"

    def test_format_volume_thousand(self, service):
        """Test volume formatting for thousands."""
        assert service.format_volume(5000) == "5.00K"

    def test_format_volume_small(self, service):
        """Test volume formatting for small values."""
        assert service.format_volume(500) == "500"
