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
        from rich.console import Console
        from io import StringIO

        result = service.format_indices(sample_quotes)

        # Render the table to a string for testing
        console = Console(file=StringIO(), force_terminal=True, width=120)
        console.print(result)
        output = console.file.getvalue()

        # Check headers are present
        assert "US Equities" in output
        assert "EU Equities" in output
        assert "Asia Equities" in output
        # Check index name is present
        assert "S&P 500" in output
        # Check change percentage is present
        assert "0.45%" in output

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
        from rich.console import Console
        from io import StringIO

        quotes = [
            Quote(symbol="FXE", name="Euro Currency Trust", price=109.58, change=0.07, changePercentage=0.06),
            Quote(symbol="FXY", name="Yen Currency Trust", price=60.19, change=-0.02, changePercentage=-0.03),
        ]
        result = service.format_forex(quotes)

        # Render the table to a string for testing
        console = Console(file=StringIO(), force_terminal=True, width=120)
        console.print(result)
        output = console.file.getvalue()

        assert "FXE" in output
        assert "Euro" in output
        assert "FXY" in output
        assert "0.06%" in output

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


class TestInternationalBonds:
    """Tests for international bond methods in DashboardService."""

    @pytest.fixture
    def mock_fmp_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def mock_eodhd_client(self):
        """Create a mock EODHD client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_fmp_client):
        """Create DashboardService with mock FMP client only."""
        return DashboardService(mock_fmp_client)

    @pytest.fixture
    def service_with_eodhd(self, mock_fmp_client, mock_eodhd_client):
        """Create DashboardService with both FMP and EODHD clients."""
        return DashboardService(mock_fmp_client, eodhd_client=mock_eodhd_client)

    @pytest.mark.asyncio
    async def test_get_international_bond_snapshot(
        self, service_with_eodhd, mock_fmp_client, mock_eodhd_client
    ):
        """Test fetching international bond snapshot."""
        # Mock US treasury rates from FMP
        mock_fmp_client.get_treasury_rates = AsyncMock(
            return_value=(
                {"month1": 4.50, "year5": 4.15, "year10": 4.28},
                None,
            )
        )

        # Mock international yields from EODHD
        mock_eodhd_client.get_international_snapshot = AsyncMock(
            return_value={
                "CA": {"1M": 4.25, "5Y": 3.10, "10Y": 3.42},
                "DE": {"5Y": 2.10, "10Y": 2.45},
                "JP": {"5Y": 0.55, "10Y": 0.92},
            }
        )

        result = await service_with_eodhd.get_international_bond_snapshot()

        assert "US" in result
        assert result["US"]["10Y"] == 4.28
        assert "CA" in result
        assert result["CA"]["10Y"] == 3.42
        assert "DE" in result
        assert result["DE"]["10Y"] == 2.45

    @pytest.mark.asyncio
    async def test_get_international_bond_snapshot_without_eodhd(
        self, service, mock_fmp_client
    ):
        """Test snapshot returns only US data when EODHD not configured."""
        mock_fmp_client.get_treasury_rates = AsyncMock(
            return_value=({"month1": 4.50, "year5": 4.15, "year10": 4.28}, None)
        )

        result = await service.get_international_bond_snapshot()

        assert "US" in result
        assert result["US"]["10Y"] == 4.28
        # Should only have US data
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_country_bond_detail_us(
        self, service_with_eodhd, mock_fmp_client
    ):
        """Test getting US bond detail uses FMP."""
        mock_fmp_client.get_treasury_rates = AsyncMock(
            return_value=(
                {
                    "month1": 4.50,
                    "month3": 4.45,
                    "month6": 4.40,
                    "year1": 4.35,
                    "year2": 4.25,
                    "year5": 4.15,
                    "year10": 4.28,
                    "year30": 4.45,
                },
                {"year10": 4.25},  # Previous day for change calculation
            )
        )

        result = await service_with_eodhd.get_country_bond_detail("US")

        assert result["country"] == "United States"
        assert "10Y" in result["yields"]
        assert result["yields"]["10Y"]["yield"] == 4.28
        mock_fmp_client.get_treasury_rates.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_country_bond_detail_international(
        self, service_with_eodhd, mock_eodhd_client
    ):
        """Test getting international bond detail uses EODHD."""
        mock_eodhd_client.get_country_yields = AsyncMock(
            return_value={
                "3M": {"close": 2.10},
                "6M": {"close": 2.15},
                "1Y": {"close": 2.20},
                "2Y": {"close": 2.25},
                "5Y": {"close": 2.35},
                "10Y": {"close": 2.45},
                "30Y": {"close": 2.60},
            }
        )

        result = await service_with_eodhd.get_country_bond_detail("DE")

        assert result["country"] == "Germany"
        assert "10Y" in result["yields"]
        assert result["yields"]["10Y"]["yield"] == 2.45
        mock_eodhd_client.get_country_yields.assert_called_once_with("DE")

    @pytest.mark.asyncio
    async def test_get_country_bond_detail_unknown_country(self, service_with_eodhd):
        """Test unknown country returns None."""
        result = await service_with_eodhd.get_country_bond_detail("XX")

        assert result is None

    def test_format_international_bond_snapshot_empty(self, service):
        """Test formatting empty snapshot."""
        result = service.format_international_bond_snapshot({})
        assert "No bond data available" in result

    def test_format_international_bond_snapshot(self, service):
        """Test formatting international bond snapshot."""
        snapshot = {
            "US": {"1M": 4.50, "5Y": 4.15, "10Y": 4.28},
            "CA": {"1M": 4.25, "5Y": 3.10, "10Y": 3.42},
            "DE": {"5Y": 2.10, "10Y": 2.45},
            "JP": {"5Y": 0.55, "10Y": 0.92},
        }
        result = service.format_international_bond_snapshot(snapshot)

        assert "INTERNATIONAL GOVERNMENT BOND YIELDS" in result
        assert "United States" in result
        assert "Germany" in result
        assert "Japan" in result
        assert "4.28" in result  # US 10Y
        assert "2.45" in result  # DE 10Y
        assert "0.92" in result  # JP 10Y

    def test_format_country_bond_detail_empty(self, service):
        """Test formatting empty country detail."""
        result = service.format_country_bond_detail(None)
        assert "No bond data available" in result

    def test_format_country_bond_detail(self, service):
        """Test formatting country bond detail."""
        detail = {
            "country": "Germany",
            "code": "DE",
            "yields": {
                "3M": {"yield": 2.10, "change": 0.05},
                "6M": {"yield": 2.15, "change": -0.02},
                "1Y": {"yield": 2.20, "change": 0.03},
                "5Y": {"yield": 2.35, "change": 0.08},
                "10Y": {"yield": 2.45, "change": 0.10},
                "30Y": {"yield": 2.60, "change": -0.05},
            },
        }
        result = service.format_country_bond_detail(detail)

        assert "GERMANY GOVERNMENT BOND YIELDS" in result
        assert "10 Year" in result
        assert "2.45" in result
        assert "Yield Curve" in result


class TestMarketSnapshot:
    """Tests for market snapshot methods in DashboardService."""

    @pytest.fixture
    def mock_fmp_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_fmp_client):
        """Create DashboardService with mock FMP client."""
        return DashboardService(mock_fmp_client)

    @pytest.fixture
    def sample_commodity_quotes(self) -> list[Quote]:
        """Create sample commodity ETF quotes."""
        return [
            Quote(symbol="GLD", name="SPDR Gold Shares", price=185.45, change=0.83, changePercentage=0.45),
            Quote(symbol="USO", name="United States Oil Fund", price=72.30, change=-0.89, changePercentage=-1.23),
            Quote(symbol="SLV", name="iShares Silver Trust", price=22.15, change=0.07, changePercentage=0.32),
            Quote(symbol="UNG", name="United States Natural Gas Fund", price=12.45, change=-0.27, changePercentage=-2.15),
            Quote(symbol="DBA", name="Invesco DB Agriculture Fund", price=24.80, change=0.04, changePercentage=0.18),
            Quote(symbol="URA", name="Global X Uranium ETF", price=28.50, change=0.42, changePercentage=1.50),
        ]

    @pytest.fixture
    def sample_sector_quotes(self) -> list[Quote]:
        """Create sample sector ETF quotes."""
        return [
            Quote(symbol="XLK", name="Technology Select Sector", price=195.42, change=2.31, changePercentage=1.2),
            Quote(symbol="XLF", name="Financial Select Sector", price=42.15, change=0.34, changePercentage=0.8),
            Quote(symbol="XLE", name="Energy Select Sector", price=87.30, change=-0.44, changePercentage=-0.5),
            Quote(symbol="XLV", name="Health Care Select Sector", price=145.67, change=0.44, changePercentage=0.3),
            Quote(symbol="XLY", name="Consumer Discretionary Select", price=182.45, change=1.09, changePercentage=0.6),
            Quote(symbol="XLI", name="Industrial Select Sector", price=120.34, change=0.96, changePercentage=0.8),
        ]

    @pytest.fixture
    def sample_index_quotes(self) -> list[Quote]:
        """Create sample index quotes for snapshot."""
        return [
            Quote(symbol="^GSPC", name="S&P 500", price=5234.18, change=23.45, changePercentage=0.45),
            Quote(symbol="^DJI", name="Dow Jones", price=38654.42, change=123.45, changePercentage=0.32),
            Quote(symbol="^IXIC", name="NASDAQ", price=16428.82, change=109.88, changePercentage=0.67),
            Quote(symbol="^RUT", name="Russell 2000", price=2045.32, change=-3.07, changePercentage=-0.15),
            Quote(symbol="^FTSE", name="FTSE 100", price=8125.45, change=26.00, changePercentage=0.32),
            Quote(symbol="^GDAXI", name="DAX", price=18432.67, change=106.91, changePercentage=0.58),
            Quote(symbol="^FCHI", name="CAC 40", price=7890.12, change=19.73, changePercentage=0.25),
            Quote(symbol="^N225", name="Nikkei 225", price=38452.12, change=473.16, changePercentage=1.23),
            Quote(symbol="^HSI", name="Hang Seng", price=17845.32, change=-80.30, changePercentage=-0.45),
            Quote(symbol="^KS11", name="KOSPI", price=2654.78, change=21.77, changePercentage=0.82),
        ]

    @pytest.mark.asyncio
    async def test_get_commodity_quotes(self, service, mock_fmp_client, sample_commodity_quotes):
        """Test fetching commodity ETF quotes."""
        mock_fmp_client.get_quotes = AsyncMock(return_value=sample_commodity_quotes)

        result = await service.get_commodity_quotes()

        assert len(result) == 6
        symbols = [q.symbol for q in result]
        assert "GLD" in symbols
        assert "USO" in symbols
        assert "URA" in symbols
        mock_fmp_client.get_quotes.assert_called_once_with(["GLD", "USO", "SLV", "UNG", "DBA", "URA"])

    @pytest.mark.asyncio
    async def test_get_sector_quotes(self, service, mock_fmp_client, sample_sector_quotes):
        """Test fetching sector ETF quotes."""
        mock_fmp_client.get_quotes = AsyncMock(return_value=sample_sector_quotes)

        result = await service.get_sector_quotes()

        assert len(result) == 6
        symbols = [q.symbol for q in result]
        assert "XLK" in symbols
        assert "XLF" in symbols
        mock_fmp_client.get_quotes.assert_called_once_with(["XLK", "XLF", "XLE", "XLV", "XLY", "XLI"])

    @pytest.mark.asyncio
    async def test_get_market_snapshot(
        self, service, mock_fmp_client, sample_index_quotes, sample_commodity_quotes, sample_sector_quotes
    ):
        """Test fetching complete market snapshot."""
        mock_fmp_client.get_world_indices = AsyncMock(return_value=sample_index_quotes)
        mock_fmp_client.get_quotes = AsyncMock(side_effect=[sample_commodity_quotes, sample_sector_quotes])
        mock_fmp_client.get_treasury_rates = AsyncMock(
            return_value=(
                {"year2": 4.25, "year5": 4.15, "year10": 4.28, "year30": 4.45},
                None,
            )
        )

        result = await service.get_market_snapshot()

        assert "indices" in result
        assert "commodities" in result
        assert "sectors" in result
        assert "bonds" in result
        assert len(result["indices"]) == 10
        assert len(result["commodities"]) == 6
        assert len(result["sectors"]) == 6

    def test_format_market_snapshot_empty(self, service):
        """Test formatting empty market snapshot."""
        result = service.format_market_snapshot({})
        assert "No snapshot data available" in result

    def test_format_market_snapshot(
        self, service, sample_index_quotes, sample_commodity_quotes, sample_sector_quotes
    ):
        """Test formatting complete market snapshot."""
        snapshot = {
            "indices": sample_index_quotes,
            "commodities": sample_commodity_quotes,
            "sectors": sample_sector_quotes,
            "bonds": {"year2": 4.25, "year5": 4.15, "year10": 4.28, "year30": 4.45},
        }
        result = service.format_market_snapshot(snapshot)

        # Check header
        assert "MARKET SNAPSHOT" in result

        # Check equity indices section
        assert "EQUITY INDICES" in result
        assert "S&P 500" in result
        assert "+0.45%" in result
        assert "NASDAQ" in result
        assert "FTSE 100" in result
        assert "Nikkei" in result

        # Check commodities section
        assert "COMMODITIES" in result
        assert "Gold" in result
        assert "Oil" in result

        # Check sectors section
        assert "SECTORS" in result
        assert "Tech" in result
        assert "Financials" in result

        # Check bonds section
        assert "BOND YIELDS" in result
        assert "2Y" in result
        assert "10Y" in result
        assert "Spread" in result

    def test_format_market_snapshot_colors(self, service):
        """Test that colors are applied correctly for gains/losses."""
        snapshot = {
            "indices": [
                Quote(symbol="^GSPC", name="S&P 500", price=5234.18, change=23.45, changePercentage=0.45),
                Quote(symbol="^DJI", name="Dow Jones", price=38654.42, change=-100.00, changePercentage=-0.26),
            ],
            "commodities": [],
            "sectors": [],
            "bonds": {},
        }
        result = service.format_market_snapshot(snapshot)

        # Green for positive
        assert "[green]" in result
        # Red for negative
        assert "[red]" in result

    def test_format_market_snapshot_spread_calculation(self, service):
        """Test that bond spread is calculated correctly."""
        snapshot = {
            "indices": [],
            "commodities": [],
            "sectors": [],
            "bonds": {"year2": 4.25, "year10": 4.28},
        }
        result = service.format_market_snapshot(snapshot)

        # Spread should be 10Y - 2Y = 4.28 - 4.25 = 0.03
        assert "+0.03%" in result or "0.03" in result
