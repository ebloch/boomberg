"""Unit tests for HistoricalService."""

from datetime import date

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import HistoricalPrice
from boomberg.services.historical import HistoricalService


class TestHistoricalService:
    """Tests for HistoricalService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create HistoricalService with mock client."""
        return HistoricalService(mock_client)

    @pytest.fixture
    def sample_prices(self) -> list[HistoricalPrice]:
        """Create sample historical prices (newest first)."""
        return [
            HistoricalPrice(
                date=date(2024, 1, 15),
                open=182.50,
                high=185.00,
                low=181.00,
                close=184.50,
                volume=55000000,
            ),
            HistoricalPrice(
                date=date(2024, 1, 14),
                open=180.00,
                high=183.50,
                low=179.50,
                close=182.50,
                volume=48000000,
            ),
            HistoricalPrice(
                date=date(2024, 1, 13),
                open=175.00,
                high=180.00,
                low=174.00,
                close=180.00,
                volume=52000000,
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_historical_prices(self, service, mock_client, sample_prices):
        """Test fetching historical prices."""
        mock_client.get_historical_prices = AsyncMock(return_value=sample_prices)
        from_date = date(2024, 1, 1)
        to_date = date(2024, 1, 15)

        result = await service.get_historical_prices("AAPL", from_date, to_date)

        assert result == sample_prices
        mock_client.get_historical_prices.assert_called_once_with(
            "AAPL", from_date, to_date
        )

    @pytest.mark.asyncio
    async def test_get_historical_prices_period(
        self, service, mock_client, sample_prices
    ):
        """Test fetching historical prices by period."""
        mock_client.get_historical_prices_period = AsyncMock(return_value=sample_prices)

        result = await service.get_historical_prices_period("AAPL", "1M")

        assert result == sample_prices
        mock_client.get_historical_prices_period.assert_called_once_with("AAPL", "1M")

    @pytest.mark.asyncio
    async def test_get_historical_prices_period_invalid(self, service):
        """Test invalid period raises error."""
        with pytest.raises(ValueError, match="Invalid period"):
            await service.get_historical_prices_period("AAPL", "2M")

    @pytest.mark.asyncio
    async def test_get_historical_prices_period_case_insensitive(
        self, service, mock_client, sample_prices
    ):
        """Test period is case insensitive."""
        mock_client.get_historical_prices_period = AsyncMock(return_value=sample_prices)

        await service.get_historical_prices_period("AAPL", "1m")

        mock_client.get_historical_prices_period.assert_called_once_with("AAPL", "1M")

    def test_calculate_returns(self, service, sample_prices):
        """Test calculating returns over period."""
        # (184.50 - 180.00) / 180.00 * 100 = 2.5%
        result = service.calculate_returns(sample_prices)
        assert result == pytest.approx(2.5, rel=0.01)

    def test_calculate_returns_empty(self, service):
        """Test calculating returns with empty list."""
        assert service.calculate_returns([]) is None

    def test_calculate_returns_single_price(self, service, sample_prices):
        """Test calculating returns with single price."""
        assert service.calculate_returns([sample_prices[0]]) is None

    def test_get_price_range(self, service, sample_prices):
        """Test getting price range over period."""
        result = service.get_price_range(sample_prices)
        assert result == (174.00, 185.00)  # (low, high)

    def test_get_price_range_empty(self, service):
        """Test price range with empty list."""
        assert service.get_price_range([]) is None

    def test_get_average_volume(self, service, sample_prices):
        """Test calculating average volume."""
        # (55M + 48M + 52M) / 3 = 51.67M
        result = service.get_average_volume(sample_prices)
        assert result == pytest.approx(51666666.67, rel=0.01)

    def test_get_average_volume_empty(self, service):
        """Test average volume with empty list."""
        assert service.get_average_volume([]) is None
