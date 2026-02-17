"""Unit tests for portfolio service."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import Quote, HistoricalPrice
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
            "AAPL": {"shares": 100, "cost_basis": 150.00},
            "GOOGL": {"shares": 50, "cost_basis": 140.00},
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
        service.add_holding("AAPL", 100, 150.00)

        mock_store.save.assert_called_once()
        saved_data = mock_store.save.call_args[0][0]
        assert "AAPL" in saved_data
        assert saved_data["AAPL"]["shares"] == 100
        assert saved_data["AAPL"]["cost_basis"] == 150.00

    def test_add_holding_uppercase(self, service, mock_store):
        """Test adding holding converts symbol to uppercase."""
        mock_store.load.return_value = {}
        service.add_holding("aapl", 100, 150.00)

        saved_data = mock_store.save.call_args[0][0]
        assert "AAPL" in saved_data

    def test_add_to_existing_holding(self, service, mock_store, sample_portfolio):
        """Test adding shares to existing holding updates average cost."""
        mock_store.load.return_value = sample_portfolio.copy()
        # Adding 100 more shares at $200 to existing 100 shares at $150
        service.add_holding("AAPL", 100, 200.00)

        saved_data = mock_store.save.call_args[0][0]
        assert saved_data["AAPL"]["shares"] == 200
        # Average cost: (100*150 + 100*200) / 200 = 175
        assert saved_data["AAPL"]["cost_basis"] == 175.00

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
        assert saved_data["AAPL"]["cost_basis"] == 150.00  # Cost basis unchanged

    @pytest.mark.asyncio
    async def test_get_portfolio_with_quotes(self, service, mock_store, mock_client, sample_portfolio, sample_quote):
        """Test getting portfolio with current quotes."""
        mock_store.load.return_value = sample_portfolio
        mock_client.get_quotes = AsyncMock(return_value=[sample_quote])
        mock_client.get_historical_prices = AsyncMock(return_value=[])

        holdings = await service.get_portfolio_with_quotes()

        assert len(holdings) >= 1
        # Find AAPL holding
        aapl = next((h for h in holdings if h.symbol == "AAPL"), None)
        assert aapl is not None
        assert aapl.shares == 100
        assert aapl.current_price == 175.00
        assert aapl.total_value == 17500.00  # 100 * 175
        assert aapl.cost_basis == 150.00
        assert aapl.total_cost == 15000.00  # 100 * 150
        assert aapl.gain_loss == 2500.00  # 17500 - 15000
        assert aapl.gain_loss_percent == pytest.approx(16.67, rel=0.01)  # 2500/15000 * 100

    @pytest.mark.asyncio
    async def test_get_portfolio_calculates_daily_change(self, service, mock_store, mock_client, sample_portfolio, sample_quote):
        """Test portfolio calculates 1D change from quote."""
        mock_store.load.return_value = {"AAPL": {"shares": 100, "cost_basis": 150.00}}
        mock_client.get_quotes = AsyncMock(return_value=[sample_quote])
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
