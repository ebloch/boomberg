"""Unit tests for DashboardService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import Quote, NewsArticle
from boomberg.services.dashboard import DashboardService


class TestDashboardService:
    """Tests for DashboardService."""

    @pytest.fixture
    def mock_fmp_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def mock_fred_client(self):
        """Create a mock FRED client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_fmp_client):
        """Create DashboardService with mock client (no FRED)."""
        return DashboardService(mock_fmp_client)

    @pytest.fixture
    def service_with_fred(self, mock_fmp_client, mock_fred_client):
        """Create DashboardService with both FMP and FRED clients."""
        return DashboardService(mock_fmp_client, mock_fred_client)

    @pytest.fixture
    def sample_quote(self) -> Quote:
        """Create a sample quote for testing."""
        return Quote(
            symbol="^GSPC",
            name="S&P 500",
            price=5234.18,
            change=23.45,
            changePercentage=0.45,
            volume=2500000000,
        )

    @pytest.fixture
    def sample_quotes(self) -> list[Quote]:
        """Create sample quotes for world indices."""
        return [
            Quote(symbol="^GSPC", name="S&P 500", price=5234.18, change=23.45, changePercentage=0.45),
            Quote(symbol="^DJI", name="Dow Jones", price=38654.42, change=123.45, changePercentage=0.32),
            Quote(symbol="^IXIC", name="NASDAQ", price=16428.82, change=109.88, changePercentage=0.67),
            Quote(symbol="^RUT", name="Russell 2000", price=2045.32, change=-3.07, changePercentage=-0.15),
            Quote(symbol="^FTSE", name="FTSE 100", price=8125.45, change=26.00, changePercentage=0.32),
            Quote(symbol="^GDAXI", name="DAX", price=18432.67, change=106.91, changePercentage=0.58),
            Quote(symbol="^N225", name="Nikkei 225", price=38452.12, change=473.16, changePercentage=1.23),
            Quote(symbol="^HSI", name="Hang Seng", price=17845.32, change=-80.30, changePercentage=-0.45),
        ]

    @pytest.mark.asyncio
    async def test_get_world_indices(self, service, mock_fmp_client, sample_quotes):
        """Test fetching world indices."""
        mock_fmp_client.get_world_indices = AsyncMock(return_value=sample_quotes)

        result = await service.get_world_indices()

        assert len(result) == 8
        mock_fmp_client.get_world_indices.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_most_active(self, service, mock_fmp_client, sample_quote):
        """Test fetching most active stocks."""
        mock_fmp_client.get_most_active = AsyncMock(return_value=[sample_quote])

        result = await service.get_most_active(limit=20)

        assert len(result) == 1
        mock_fmp_client.get_most_active.assert_called_once_with(20)

    @pytest.mark.asyncio
    async def test_get_treasury_rates(self, service, mock_fmp_client):
        """Test fetching treasury rates."""
        mock_rates = {
            "date": "2025-01-15",
            "month1": 5.25,
            "month3": 5.22,
            "year10": 4.28,
            "year30": 4.45,
        }
        mock_fmp_client.get_treasury_rates = AsyncMock(return_value=mock_rates)

        result = await service.get_treasury_rates()

        assert result["month1"] == 5.25
        mock_fmp_client.get_treasury_rates.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_forex_rates(self, service, mock_fmp_client):
        """Test fetching forex rates."""
        mock_rates = [
            {"ticker": "EURUSD", "bid": 1.0843, "ask": 1.0847, "changes": 0.12},
            {"ticker": "GBPUSD", "bid": 1.2652, "ask": 1.2656, "changes": -0.08},
        ]
        mock_fmp_client.get_forex_quotes = AsyncMock(return_value=mock_rates)

        result = await service.get_forex_rates()

        assert len(result) == 2
        mock_fmp_client.get_forex_quotes.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_economic_stats_without_fred(self, service):
        """Test economic stats returns empty dict when FRED not configured."""
        result = await service.get_economic_stats()

        assert result == {}

    @pytest.mark.asyncio
    async def test_get_economic_stats_with_fred(self, service_with_fred, mock_fred_client):
        """Test economic stats returns data when FRED is configured."""
        mock_stats = {
            "GDP": {"date": "2024-10-01", "value": "27963.5"},
            "Unemployment": {"date": "2025-01-01", "value": "3.7"},
        }
        mock_fred_client.get_economic_indicators = AsyncMock(return_value=mock_stats)

        result = await service_with_fred.get_economic_stats()

        assert "GDP" in result
        mock_fred_client.get_economic_indicators.assert_called_once()

    def test_format_indices_empty(self, service):
        """Test formatting empty indices list."""
        result = service.format_indices([])
        assert "No index data available" in result

    def test_format_indices(self, service, sample_quotes):
        """Test formatting world indices."""
        result = service.format_indices(sample_quotes)

        assert "WORLD EQUITY INDICES" in result
        assert "US MARKETS" in result
        assert "EUROPE" in result
        assert "ASIA" in result
        assert "S&P 500" in result
        assert "0.45%" in result

    def test_format_most_active_empty(self, service):
        """Test formatting empty most active list."""
        result = service.format_most_active([])
        assert "No data available" in result

    def test_format_most_active(self, service):
        """Test formatting market movers."""
        quotes = [
            Quote(symbol="NVDA", name="NVIDIA", price=892.45, change=67.12, changePercentage=8.2, volume=125400000),
            Quote(symbol="TSLA", name="Tesla", price=245.67, change=11.23, changePercentage=4.8, volume=98200000),
        ]
        result = service.format_most_active(quotes)

        assert "MARKET MOVERS" in result
        assert "NVDA" in result
        assert "TSLA" in result
        assert "8.20%" in result

    def test_format_treasury_rates_empty(self, service):
        """Test formatting empty treasury rates."""
        result = service.format_treasury_rates({})
        assert "No treasury rate data available" in result

    def test_format_treasury_rates(self, service):
        """Test formatting treasury rates."""
        rates = {
            "date": "2025-01-15",
            "month1": 5.25,
            "month3": 5.22,
            "year10": 4.28,
            "year30": 4.45,
        }
        result = service.format_treasury_rates(rates)

        assert "US TREASURY YIELDS" in result
        assert "1 Month" in result
        assert "5.25%" in result
        assert "10 Year" in result
        assert "4.28%" in result

    def test_format_forex_empty(self, service):
        """Test formatting empty currency ETFs."""
        result = service.format_forex([])
        assert "No currency data available" in result

    def test_format_forex(self, service):
        """Test formatting currency ETFs."""
        quotes = [
            Quote(symbol="FXE", name="Euro Currency Trust", price=109.58, change=0.07, changePercentage=0.06),
            Quote(symbol="FXY", name="Yen Currency Trust", price=60.19, change=-0.02, changePercentage=-0.03),
        ]
        result = service.format_forex(quotes)

        assert "CURRENCY ETFs" in result
        assert "FXE" in result
        assert "Euro" in result
        assert "FXY" in result
        assert "0.06%" in result

    def test_format_economic_stats_empty(self, service):
        """Test formatting empty economic stats."""
        result = service.format_economic_stats({})
        assert "No economic data available" in result
        assert "FRED_API_KEY" in result

    def test_format_economic_stats(self, service):
        """Test formatting economic stats."""
        stats = {
            "GDP": {"date": "2024-10-01", "value": "27963.5"},
            "Unemployment": {"date": "2025-01-01", "value": "3.7"},
            "CPI": {"date": "2025-01-01", "value": "315.6"},
            "Fed Funds Rate": {"date": "2025-01-01", "value": "5.33"},
            "10Y Treasury": {"date": "2025-01-15", "value": "4.28"},
        }
        result = service.format_economic_stats(stats)

        assert "ECONOMIC STATISTICS" in result
        assert "GDP" in result
        assert "Unemployment" in result
        assert "3.70%" in result

    def test_format_volume_millions(self, service):
        """Test volume formatting for millions."""
        assert service._format_volume(125400000) == "125.4M"

    def test_format_volume_billions(self, service):
        """Test volume formatting for billions."""
        assert service._format_volume(2500000000) == "2.5B"

    def test_format_volume_thousands(self, service):
        """Test volume formatting for thousands."""
        assert service._format_volume(45000) == "45.0K"

    def test_format_volume_small(self, service):
        """Test volume formatting for small numbers."""
        assert service._format_volume(500) == "500"
