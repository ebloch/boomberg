"""Unit tests for portfolio service."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import Quote, HistoricalPrice, StockPriceChange
from boomberg.services.portfolio import PortfolioService, PortfolioHolding


class TestPortfolioService:
    """Tests for PortfolioService."""

    @pytest.fixture
    def mock_store(self):
        """Create mock portfolio store."""
        store = MagicMock()
        store.load.return_value = {}
        return store

    @pytest.fixture
    def mock_client(self):
        """Create mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_store, mock_client):
        """Create portfolio service with mocks."""
        return PortfolioService(mock_store, mock_client)

    @pytest.fixture
    def sample_portfolio(self):
        """Sample portfolio data."""
        return {
            "AAPL": {"shares": 100, "total_cost": 15000.00},  # 100 shares * $150
            "GOOGL": {"shares": 50, "total_cost": 7000.00},   # 50 shares * $140
        }

    @pytest.fixture
    def sample_quote(self) -> Quote:
        """Sample quote for AAPL."""
        return Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=175.00,
            change=2.50,
            changePercentage=1.45,
            volume=50000000,
            exchange="NASDAQ",
        )

    def test_get_holdings_empty(self, service, mock_store):
        """Test getting holdings when portfolio is empty."""
        mock_store.load.return_value = {}
        result = service.get_holdings()
        assert result == {}

    def test_get_holdings(self, service, mock_store, sample_portfolio):
        """Test getting holdings."""
        mock_store.load.return_value = sample_portfolio
        result = service.get_holdings()
        assert "AAPL" in result
        assert result["AAPL"]["shares"] == 100

    def test_add_holding(self, service, mock_store):
        """Test adding a new holding."""
        mock_store.load.return_value = {}
        service.add_holding("AAPL", 100, 15000.00)  # 100 shares, $15000 total cost

        mock_store.save.assert_called_once()
        saved_data = mock_store.save.call_args[0][0]
        assert "AAPL" in saved_data
        assert saved_data["AAPL"]["shares"] == 100
        assert saved_data["AAPL"]["total_cost"] == 15000.00

    def test_add_holding_uppercase(self, service, mock_store):
        """Test adding holding converts symbol to uppercase."""
        mock_store.load.return_value = {}
        service.add_holding("aapl", 100, 150.00)

        saved_data = mock_store.save.call_args[0][0]
        assert "AAPL" in saved_data

    def test_add_to_existing_holding(self, service, mock_store, sample_portfolio):
        """Test adding shares to existing holding combines total cost."""
        mock_store.load.return_value = sample_portfolio.copy()
        # Adding 100 more shares with $20000 total cost to existing 100 shares with $15000 total cost
        service.add_holding("AAPL", 100, 20000.00)

        saved_data = mock_store.save.call_args[0][0]
        assert saved_data["AAPL"]["shares"] == 200
        # Total cost: 15000 + 20000 = 35000
        assert saved_data["AAPL"]["total_cost"] == 35000.00

    def test_remove_holding(self, service, mock_store, sample_portfolio):
        """Test removing a holding completely."""
        mock_store.load.return_value = sample_portfolio.copy()
        service.remove_holding("AAPL")

        saved_data = mock_store.save.call_args[0][0]
        assert "AAPL" not in saved_data
        assert "GOOGL" in saved_data

    def test_remove_holding_not_found(self, service, mock_store, sample_portfolio):
        """Test removing non-existent holding raises error."""
        mock_store.load.return_value = sample_portfolio.copy()
        with pytest.raises(KeyError):
            service.remove_holding("MSFT")

    def test_update_shares(self, service, mock_store, sample_portfolio):
        """Test updating share count."""
        mock_store.load.return_value = sample_portfolio.copy()
        service.update_shares("AAPL", 150)

        saved_data = mock_store.save.call_args[0][0]
        assert saved_data["AAPL"]["shares"] == 150
        assert saved_data["AAPL"]["total_cost"] == 15000.00  # Total cost unchanged

    @pytest.mark.asyncio
    async def test_get_portfolio_with_quotes(self, service, mock_store, mock_client, sample_portfolio, sample_quote):
        """Test getting portfolio with current quotes."""
        mock_store.load.return_value = sample_portfolio
        mock_client.get_quotes = AsyncMock(return_value=[sample_quote])
        mock_client.get_stock_price_changes = AsyncMock(return_value=[])
        mock_client.get_historical_prices = AsyncMock(return_value=[])

        holdings = await service.get_portfolio_with_quotes()

        assert len(holdings) >= 1
        # Find AAPL holding
        aapl = next((h for h in holdings if h.symbol == "AAPL"), None)
        assert aapl is not None
        assert aapl.shares == 100
        assert aapl.current_price == 175.00
        assert aapl.total_value == 17500.00  # 100 * 175
        assert aapl.cost_basis == 150.00  # 15000 / 100 (calculated per-share)
        assert aapl.total_cost == 15000.00  # From storage directly
        assert aapl.gain_loss == 2500.00  # 17500 - 15000
        assert aapl.gain_loss_percent == pytest.approx(16.67, rel=0.01)  # 2500/15000 * 100

    @pytest.mark.asyncio
    async def test_get_portfolio_calculates_daily_change(self, service, mock_store, mock_client, sample_portfolio, sample_quote):
        """Test portfolio calculates 1D change from quote."""
        mock_store.load.return_value = {"AAPL": {"shares": 100, "total_cost": 15000.00}}
        mock_client.get_quotes = AsyncMock(return_value=[sample_quote])
        mock_client.get_stock_price_changes = AsyncMock(return_value=[])
        mock_client.get_historical_prices = AsyncMock(return_value=[])

        holdings = await service.get_portfolio_with_quotes()
        aapl = holdings[0]

        # Daily change should come from quote
        assert aapl.change_1d_pct == 1.45
        assert aapl.change_1d_value == 250.00  # 100 shares * $2.50 change

    def test_format_currency(self, service):
        """Test currency formatting."""
        assert service.format_currency(1234.56) == "$1,234.56"
        assert service.format_currency(-500.00) == "-$500.00"
        assert service.format_currency(1000000) == "$1,000,000.00"

    def test_format_percent(self, service):
        """Test percent formatting."""
        assert service.format_percent(5.25) == "+5.25%"
        assert service.format_percent(-3.50) == "-3.50%"
        assert service.format_percent(0) == "+0.00%"

    def test_holding_dataclass(self):
        """Test PortfolioHolding dataclass."""
        holding = PortfolioHolding(
            symbol="AAPL",
            name="Apple Inc.",
            shares=100,
            cost_basis=150.00,
            current_price=175.00,
            total_value=17500.00,
            total_cost=15000.00,
            gain_loss=2500.00,
            gain_loss_percent=16.67,
            change_1d_value=250.00,
            change_1d_pct=1.45,
            change_mtd_value=500.00,
            change_mtd_pct=2.94,
            change_ytd_value=1000.00,
            change_ytd_pct=6.06,
            exchange="NASDAQ",
        )
        assert holding.symbol == "AAPL"
        assert holding.total_value == 17500.00

    @pytest.mark.asyncio
    async def test_gain_loss_uses_total_cost_directly(self, service, mock_store, mock_client):
        """Test that gain/loss uses total_cost from storage, not shares * cost_basis.

        This tests the fix for the bug where entering total cost (e.g., PA CB 80 26624)
        would be multiplied by shares again, causing wildly incorrect gain/loss.
        """
        # Store total_cost of $26,624 for 80 shares (per-share would be $332.80)
        mock_store.load.return_value = {
            "CB": {"shares": 80, "total_cost": 26624.00}
        }

        quote = Quote(
            symbol="CB",
            name="Chubb Limited",
            price=331.89,
            change=7.00,
            changePercentage=2.14,
            volume=1000000,
            exchange="NYSE",
        )
        mock_client.get_quotes = AsyncMock(return_value=[quote])
        mock_client.get_stock_price_changes = AsyncMock(return_value=[])
        mock_client.get_historical_prices = AsyncMock(return_value=[])

        holdings = await service.get_portfolio_with_quotes()
        cb = holdings[0]

        # total_value = 80 * 331.89 = 26,551.20
        assert cb.total_value == pytest.approx(26551.20, rel=0.01)
        # total_cost should be 26,624 (from storage, NOT 80 * 26624)
        assert cb.total_cost == pytest.approx(26624.00, rel=0.01)
        # gain_loss = 26551.20 - 26624 = -72.80
        assert cb.gain_loss == pytest.approx(-72.80, rel=0.1)
        # gain_loss_percent = -72.80 / 26624 * 100 = -0.27%
        assert cb.gain_loss_percent == pytest.approx(-0.27, rel=0.1)

    @pytest.mark.asyncio
    async def test_ytd_uses_fmp_precalculated_value(self, service, mock_store, mock_client):
        """Test that YTD uses FMP's precalculated stock-price-change value instead of calculating from historical."""
        mock_store.load.return_value = {
            "AAPL": {"shares": 100, "total_cost": 15000.00}
        }

        quote = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=175.00,
            change=2.50,
            changePercentage=1.45,
            volume=50000000,
            exchange="NASDAQ",
        )

        # FMP's precalculated YTD change
        price_change = StockPriceChange(
            symbol="AAPL",
            ytd=12.5,  # 12.5% YTD return from FMP
        )

        mock_client.get_quotes = AsyncMock(return_value=[quote])
        mock_client.get_stock_price_changes = AsyncMock(return_value=[price_change])
        mock_client.get_historical_prices = AsyncMock(return_value=[])

        holdings = await service.get_portfolio_with_quotes()
        aapl = holdings[0]

        # YTD % should come directly from FMP, not calculated
        assert aapl.change_ytd_pct == 12.5

        # YTD value = shares * price * (ytd_pct / 100) / (1 + ytd_pct / 100)
        # Or more simply: price at YTD start = 175 / 1.125 = 155.56
        # YTD value change = 100 * (175 - 155.56) = 1944.44
        expected_ytd_value = 100 * (175.00 - (175.00 / 1.125))
        assert aapl.change_ytd_value == pytest.approx(expected_ytd_value, rel=0.01)

        # Verify get_stock_price_changes was called
        mock_client.get_stock_price_changes.assert_called_once_with(["AAPL"])
