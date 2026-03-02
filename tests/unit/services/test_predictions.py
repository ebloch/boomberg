"""Unit tests for PredictionMarketService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.kalshi_models import KalshiMarket
from boomberg.api.exceptions import APIError
from boomberg.services.predictions import (
    PredictionMarketService,
    ECONOMIC_SERIES,
    SERIES_CATEGORIES,
)


class TestPredictionMarketService:
    """Tests for PredictionMarketService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Kalshi client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create PredictionMarketService with mock client."""
        return PredictionMarketService(mock_client)

    @pytest.fixture
    def sample_market(self) -> KalshiMarket:
        """Create a sample market."""
        return KalshiMarket(
            ticker="FED-25MAR-T4.75",
            title="Will the Fed cut rates in March 2025?",
            status="active",
            yes_bid=62,
            no_bid=36,
            yes_ask=64,
            no_ask=38,
            last_price=63,
            previous_price=60,
            volume_24h=125400,
            open_interest=450200,
            close_time="2025-03-15T16:00:00Z",
        )

    @pytest.fixture
    def sample_markets(self, sample_market) -> list[KalshiMarket]:
        """Create sample markets list."""
        market2 = KalshiMarket(
            ticker="BTC-100K-EOY",
            title="Will BTC hit $100K by EOY?",
            status="active",
            yes_bid=45,
            no_bid=53,
            last_price=45,
            previous_price=47,
            volume_24h=89200,
        )
        market3 = KalshiMarket(
            ticker="LOW-VOLUME",
            title="Low volume market",
            status="active",
            volume_24h=100,
        )
        return [market3, sample_market, market2]  # Not sorted by volume

    @pytest.mark.asyncio
    async def test_get_featured_markets_uses_economic_series(
        self, service, mock_client, sample_markets
    ):
        """Test that get_featured_markets fetches from economic series."""
        mock_client.get_markets_by_series = AsyncMock(return_value=sample_markets)

        await service.get_featured_markets()

        # Should call get_markets_by_series for each economic series
        assert mock_client.get_markets_by_series.call_count == len(ECONOMIC_SERIES)
        # Check that it's called with the expected series
        called_series = [
            call.args[0] for call in mock_client.get_markets_by_series.call_args_list
        ]
        assert set(called_series) == set(ECONOMIC_SERIES)

    @pytest.mark.asyncio
    async def test_get_featured_markets_sorted_by_volume(
        self, service, mock_client, sample_markets
    ):
        """Test that featured markets are sorted by volume descending."""
        mock_client.get_markets_by_series = AsyncMock(return_value=sample_markets)

        result = await service.get_featured_markets(limit=15)

        # Should be sorted by volume descending
        assert result[0].ticker == "FED-25MAR-T4.75"  # 125400 volume
        assert result[1].ticker == "BTC-100K-EOY"  # 89200 volume
        assert result[2].ticker == "LOW-VOLUME"  # 100 volume

    @pytest.mark.asyncio
    async def test_get_featured_markets_dedupes_by_ticker(self, service, mock_client):
        """Test that featured markets are deduped by ticker."""
        market1 = KalshiMarket(
            ticker="FED-25MAR-T4.75",
            title="Fed Rate",
            status="active",
            volume_24h=100000,
        )
        market2 = KalshiMarket(
            ticker="FED-25MAR-T4.75",  # Same ticker
            title="Fed Rate (dupe)",
            status="active",
            volume_24h=50000,
        )

        def side_effect(series):
            if series == "KXFED":
                return [market1]
            elif series == "KXFEDDECISION":
                return [market2]
            return []

        mock_client.get_markets_by_series = AsyncMock(side_effect=side_effect)

        result = await service.get_featured_markets()

        # Should only have one market with ticker FED-25MAR-T4.75
        tickers = [m.ticker for m in result]
        assert tickers.count("FED-25MAR-T4.75") == 1

    @pytest.mark.asyncio
    async def test_get_featured_markets_handles_api_errors(self, service, mock_client):
        """Test that API errors for individual series are handled gracefully."""
        market = KalshiMarket(
            ticker="CPI-TEST",
            title="CPI Market",
            status="active",
            volume_24h=50000,
        )

        def side_effect(series):
            if series == "KXFED":
                raise APIError("API Error", 500)
            elif series == "KXCPI":
                return [market]
            return []

        mock_client.get_markets_by_series = AsyncMock(side_effect=side_effect)

        result = await service.get_featured_markets()

        # Should still return markets from successful calls
        assert len(result) >= 1
        assert any(m.ticker == "CPI-TEST" for m in result)

    @pytest.mark.asyncio
    async def test_get_featured_markets_respects_limit(self, service, mock_client):
        """Test that featured markets respects the limit parameter."""
        markets = [
            KalshiMarket(
                ticker=f"MARKET-{i}",
                title=f"Market {i}",
                status="active",
                volume_24h=1000 * i,
            )
            for i in range(20)
        ]
        mock_client.get_markets_by_series = AsyncMock(return_value=markets)

        result = await service.get_featured_markets(limit=5)

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_get_market(self, service, mock_client, sample_market):
        """Test fetching a single market."""
        mock_client.get_market = AsyncMock(return_value=sample_market)

        result = await service.get_market("FED-25MAR-T4.75")

        assert result == sample_market
        mock_client.get_market.assert_called_once_with("FED-25MAR-T4.75")

    def test_format_price_cents(self, service):
        """Test formatting price in cents."""
        assert service.format_price_cents(62) == "62c"
        assert service.format_price_cents(5) == "5c"
        assert service.format_price_cents(100) == "100c"

    def test_format_price_cents_none(self, service):
        """Test formatting price when None."""
        assert service.format_price_cents(None) == "-"

    def test_format_change(self, service, sample_market):
        """Test formatting price change."""
        result = service.format_change(sample_market)
        assert result == "+3c"

    def test_format_change_negative(self, service):
        """Test formatting negative price change."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            status="active",
            last_price=45,
            previous_price=47,
        )
        result = service.format_change(market)
        assert result == "-2c"

    def test_format_change_zero(self, service):
        """Test formatting zero price change."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            status="active",
            last_price=50,
            previous_price=50,
        )
        result = service.format_change(market)
        assert result == "0c"

    def test_format_volume(self, service):
        """Test volume formatting."""
        assert service.format_volume(125400) == "125.4K"
        assert service.format_volume(1500000) == "1.5M"
        assert service.format_volume(500) == "500"

    def test_get_change_direction_up(self, service, sample_market):
        """Test change direction for positive change."""
        assert service.get_change_direction(sample_market) == "up"

    def test_get_change_direction_down(self, service):
        """Test change direction for negative change."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            status="active",
            last_price=45,
            previous_price=47,
        )
        assert service.get_change_direction(market) == "down"

    def test_get_change_direction_neutral(self, service):
        """Test change direction for zero change."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            status="active",
        )
        assert service.get_change_direction(market) == "neutral"

    def test_truncate_title(self, service):
        """Test title truncation."""
        long_title = "This is a very long market title that should be truncated"
        assert service.truncate_title(long_title, 30) == "This is a very long market ..."

    def test_truncate_title_short(self, service):
        """Test title truncation when title is short enough."""
        short_title = "Short title"
        assert service.truncate_title(short_title, 30) == "Short title"

    @pytest.mark.asyncio
    async def test_get_featured_markets_sets_series_ticker(self, service, mock_client):
        """Test that markets have series_ticker set."""
        market = KalshiMarket(ticker="FED-TEST", title="Test", status="active")
        mock_client.get_markets_by_series = AsyncMock(return_value=[market])

        result = await service.get_featured_markets()

        # Markets from KXFED series should have series_ticker set
        assert any(m.series_ticker is not None for m in result)

    @pytest.mark.asyncio
    async def test_get_markets_grouped_by_category(self, service, mock_client):
        """Test grouping markets by category."""
        fed_market = KalshiMarket(
            ticker="FED-1", title="Fed", status="active", series_ticker="KXFED"
        )
        cpi_market = KalshiMarket(
            ticker="CPI-1", title="CPI", status="active", series_ticker="KXCPI"
        )

        def side_effect(series):
            if series == "KXFED":
                return [fed_market]
            elif series == "KXCPI":
                return [cpi_market]
            return []

        mock_client.get_markets_by_series = AsyncMock(side_effect=side_effect)

        grouped = await service.get_markets_grouped_by_category()

        assert "Fed Rates" in grouped
        assert "Inflation (CPI)" in grouped
        assert len(grouped["Fed Rates"]) >= 1
        assert len(grouped["Inflation (CPI)"]) >= 1

    def test_series_categories_mapping_exists(self):
        """Test that SERIES_CATEGORIES mapping is defined."""
        assert "KXFED" in SERIES_CATEGORIES
        assert "KXCPI" in SERIES_CATEGORIES
        assert SERIES_CATEGORIES["KXFED"] == "Fed Rates"
        assert SERIES_CATEGORIES["KXCPI"] == "Inflation (CPI)"
