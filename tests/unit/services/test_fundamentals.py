"""Unit tests for FundamentalsService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import CompanyProfile
from boomberg.services.fundamentals import FundamentalsService


class TestFundamentalsService:
    """Tests for FundamentalsService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create FundamentalsService with mock client."""
        return FundamentalsService(mock_client)

    @pytest.fixture
    def sample_profile(self) -> CompanyProfile:
        """Create a sample company profile."""
        return CompanyProfile(
            symbol="AAPL",
            company_name="Apple Inc.",
            exchange="NASDAQ",
            industry="Consumer Electronics",
            sector="Technology",
            description="Apple designs and manufactures smartphones.",
            ceo="Tim Cook",
            website="https://www.apple.com",
            market_cap=2890000000000,
            price=185.50,
            country="US",
            city="Cupertino",
            employees=164000,
        )

    @pytest.mark.asyncio
    async def test_get_profile(self, service, mock_client, sample_profile):
        """Test fetching company profile."""
        mock_client.get_company_profile = AsyncMock(return_value=sample_profile)

        result = await service.get_profile("AAPL")

        assert result == sample_profile
        mock_client.get_company_profile.assert_called_once_with("AAPL")

    def test_format_market_cap_trillion(self, service):
        """Test market cap formatting for trillions."""
        assert service.format_market_cap(2890000000000) == "$2.89T"

    def test_format_market_cap_billion(self, service):
        """Test market cap formatting for billions."""
        assert service.format_market_cap(150000000000) == "$150.00B"

    def test_format_market_cap_million(self, service):
        """Test market cap formatting for millions."""
        assert service.format_market_cap(500000000) == "$500.00M"

    def test_format_market_cap_none(self, service):
        """Test market cap formatting for None."""
        assert service.format_market_cap(None) == "N/A"

    def test_format_employees_thousands(self, service):
        """Test employee count formatting for thousands."""
        assert service.format_employees(164000) == "164.0K"

    def test_format_employees_small(self, service):
        """Test employee count formatting for small numbers."""
        assert service.format_employees(500) == "500"

    def test_format_employees_none(self, service):
        """Test employee count formatting for None."""
        assert service.format_employees(None) == "N/A"

    def test_get_profile_summary(self, service, sample_profile):
        """Test getting profile summary."""
        summary = service.get_profile_summary(sample_profile)

        assert summary["Company"] == "Apple Inc."
        assert summary["Symbol"] == "AAPL"
        assert summary["Exchange"] == "NASDAQ"
        assert summary["Sector"] == "Technology"
        assert summary["Industry"] == "Consumer Electronics"
        assert summary["CEO"] == "Tim Cook"
        assert summary["Market Cap"] == "$2.89T"
        assert summary["Employees"] == "164.0K"
        assert summary["Country"] == "US"
        assert summary["Website"] == "https://www.apple.com"

    def test_get_profile_summary_with_missing_data(self, service):
        """Test profile summary handles missing data."""
        profile = CompanyProfile(symbol="TEST", company_name="Test Corp", price=10.0)
        summary = service.get_profile_summary(profile)

        assert summary["Sector"] == "N/A"
        assert summary["CEO"] == "N/A"
        assert summary["Market Cap"] == "N/A"
