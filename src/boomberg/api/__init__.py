"""FMP API client and models."""

from boomberg.api.client import FMPClient
from boomberg.api.exceptions import APIError, RateLimitError, SymbolNotFoundError
from boomberg.api.models import (
    CompanyProfile,
    HistoricalPrice,
    NewsArticle,
    Quote,
    SearchResult,
)

__all__ = [
    "FMPClient",
    "APIError",
    "RateLimitError",
    "SymbolNotFoundError",
    "Quote",
    "HistoricalPrice",
    "CompanyProfile",
    "NewsArticle",
    "SearchResult",
]
