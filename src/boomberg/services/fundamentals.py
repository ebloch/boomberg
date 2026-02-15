"""Fundamentals service for company data."""

from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import CompanyProfile


class FundamentalsService:
    """Service for fetching company fundamentals."""

    def __init__(self, client: FMPClient):
        self._client = client

    async def get_profile(self, symbol: str) -> CompanyProfile:
        """Get company profile and fundamentals."""
        return await self._client.get_company_profile(symbol)

    def format_market_cap(self, market_cap: Optional[float]) -> str:
        """Format market cap in human-readable form."""
        if market_cap is None:
            return "N/A"
        if market_cap >= 1e12:
            return f"${market_cap / 1e12:.2f}T"
        if market_cap >= 1e9:
            return f"${market_cap / 1e9:.2f}B"
        if market_cap >= 1e6:
            return f"${market_cap / 1e6:.2f}M"
        return f"${market_cap:,.0f}"

    def format_employees(self, employees: Optional[int]) -> str:
        """Format employee count."""
        if employees is None:
            return "N/A"
        if employees >= 1000:
            return f"{employees / 1000:.1f}K"
        return f"{employees:,}"

    def get_profile_summary(self, profile: CompanyProfile) -> dict[str, str]:
        """Get a summary of key profile data."""
        return {
            "Company": profile.company_name,
            "Symbol": profile.symbol,
            "Exchange": profile.exchange,
            "Sector": profile.sector or "N/A",
            "Industry": profile.industry or "N/A",
            "CEO": profile.ceo or "N/A",
            "Market Cap": self.format_market_cap(profile.market_cap),
            "Employees": self.format_employees(profile.employees),
            "Country": profile.country or "N/A",
            "Website": profile.website or "N/A",
        }
