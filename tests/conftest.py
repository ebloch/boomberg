"""Shared test fixtures and configuration."""

import pytest

from boomberg.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with dummy API key."""
    return Settings(
        fmp_api_key="test_api_key",
        fmp_base_url="https://financialmodelingprep.com/stable",
        fred_api_key="test_fred_key",
        fred_base_url="https://api.stlouisfed.org/fred",
        refresh_interval=10.0,
        watchlist_path="test_watchlists.json",
    )


@pytest.fixture
def sample_quote_data() -> dict:
    """Sample quote API response data."""
    return {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "price": 185.50,
        "change": 2.35,
        "changePercentage": 1.28,
        "dayLow": 183.00,
        "dayHigh": 186.50,
        "yearLow": 164.08,
        "yearHigh": 199.62,
        "marketCap": 2890000000000,
        "volume": 52500000,
        "avgVolume": 58000000,
        "open": 184.00,
        "previousClose": 183.15,
        "eps": 6.13,
        "pe": 30.26,
        "exchange": "NASDAQ",
    }


@pytest.fixture
def sample_historical_data() -> list[dict]:
    """Sample historical price API response data."""
    return [
        {
            "date": "2024-01-15",
            "open": 182.50,
            "high": 185.00,
            "low": 181.00,
            "close": 184.50,
            "volume": 55000000,
            "adjClose": 184.50,
        },
        {
            "date": "2024-01-14",
            "open": 180.00,
            "high": 183.50,
            "low": 179.50,
            "close": 182.50,
            "volume": 48000000,
            "adjClose": 182.50,
        },
    ]


@pytest.fixture
def sample_profile_data() -> dict:
    """Sample company profile API response data."""
    return {
        "symbol": "AAPL",
        "companyName": "Apple Inc.",
        "exchange": "NASDAQ",
        "industry": "Consumer Electronics",
        "sector": "Technology",
        "description": "Apple designs, manufactures, and markets smartphones.",
        "ceo": "Tim Cook",
        "website": "https://www.apple.com",
        "mktCap": 2890000000000,
        "price": 185.50,
        "beta": 1.28,
        "volAvg": 58000000,
        "lastDiv": 0.96,
        "country": "US",
        "city": "Cupertino",
        "fullTimeEmployees": 164000,
        "ipoDate": "1980-12-12",
    }


@pytest.fixture
def sample_news_data() -> list[dict]:
    """Sample news API response data."""
    return [
        {
            "symbol": "AAPL",
            "title": "Apple Reports Record Q4 Earnings",
            "text": "Apple Inc reported record revenue in Q4...",
            "publishedDate": "2024-01-15T14:30:00.000Z",
            "site": "Bloomberg",
            "url": "https://example.com/news/1",
            "image": "https://example.com/image.jpg",
        },
    ]


@pytest.fixture
def sample_search_data() -> list[dict]:
    """Sample search API response data."""
    return [
        {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "currency": "USD",
            "exchangeFullName": "NASDAQ Global Select",
            "exchange": "NASDAQ",
        },
        {
            "symbol": "APC.F",
            "name": "Apple Inc.",
            "currency": "EUR",
            "exchangeFullName": "Frankfurt Stock Exchange",
            "exchange": "FSX",
        },
    ]
