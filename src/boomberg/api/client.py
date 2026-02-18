"""Async FMP API client."""

from datetime import date, timedelta
from typing import Optional

import httpx

from boomberg.api.exceptions import APIError, RateLimitError, SymbolNotFoundError
from boomberg.api.models import (
    BalanceSheet,
    CashFlowStatement,
    CompanyProfile,
    FinancialRatiosTTM,
    HistoricalPrice,
    IncomeStatement,
    KeyMetricsTTM,
    NewsArticle,
    Quote,
    SearchResult,
    StockPriceChange,
)
from boomberg.config import Settings, get_settings


class FMPClient:
    """Async client for Financial Modeling Prep API (stable endpoints)."""

    def __init__(self, settings: Optional[Settings] = None):
        self._settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "FMPClient":
        self._client = httpx.AsyncClient(
            base_url=self._settings.fmp_base_url,
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("Client not initialized. Use async context manager.")
        return self._client

    def _add_api_key(self, params: dict) -> dict:
        """Add API key to request parameters."""
        return {**params, "apikey": self._settings.fmp_api_key}

    async def _get(self, endpoint: str, params: dict | None = None) -> list | dict:
        """Make GET request to API."""
        params = self._add_api_key(params or {})
        response = await self.client.get(endpoint, params=params)

        if response.status_code == 429:
            raise RateLimitError()
        if response.status_code >= 400:
            raise APIError(f"API request failed: {response.text}", response.status_code)

        return response.json()

    async def get_quote(self, symbol: str) -> Quote:
        """Get real-time quote for a symbol."""
        # Stable API: /stable/quote?symbol=AAPL
        params = {"symbol": symbol.upper()}
        data = await self._get("/quote", params)
        if not data or (isinstance(data, list) and len(data) == 0):
            raise SymbolNotFoundError(symbol)
        quote_data = data[0] if isinstance(data, list) else data
        return Quote.model_validate(quote_data)

    async def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get real-time quotes for multiple symbols."""
        if not symbols:
            return []
        # Stable API doesn't support batch quotes, so fetch individually
        import asyncio

        async def fetch_quote(symbol: str) -> Quote | None:
            try:
                return await self.get_quote(symbol)
            except SymbolNotFoundError:
                return None

        results = await asyncio.gather(*[fetch_quote(s) for s in symbols])
        return [q for q in results if q is not None]

    async def get_stock_price_changes(self, symbols: list[str]) -> list[StockPriceChange]:
        """Get price change percentages for multiple symbols.

        Returns price changes over various time periods (1D, 5D, 1M, YTD, 1Y, etc.)
        directly from FMP without needing to calculate from historical prices.
        """
        if not symbols:
            return []

        import asyncio

        async def fetch_change(symbol: str) -> StockPriceChange | None:
            try:
                params = {"symbol": symbol.upper()}
                data = await self._get("/stock-price-change", params)
                if not data or (isinstance(data, list) and len(data) == 0):
                    return None
                change_data = data[0] if isinstance(data, list) else data
                return StockPriceChange.model_validate(change_data)
            except Exception:
                return None

        results = await asyncio.gather(*[fetch_change(s) for s in symbols])
        return [c for c in results if c is not None]

    async def get_historical_prices(
        self,
        symbol: str,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> list[HistoricalPrice]:
        """Get historical price data for a symbol."""
        # Stable API: /stable/historical-price-eod/full?symbol=AAPL
        params = {"symbol": symbol.upper()}
        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        data = await self._get("/historical-price-eod/full", params)
        if not data:
            return []

        # Stable API returns list directly, not nested under "historical"
        if isinstance(data, dict) and "historical" in data:
            data = data["historical"]

        return [HistoricalPrice.model_validate(item) for item in data]

    async def get_historical_prices_period(
        self, symbol: str, period: str = "1M"
    ) -> list[HistoricalPrice]:
        """Get historical prices for a predefined period.

        Args:
            symbol: Stock symbol
            period: One of 1D, 1W, 1M, 3M, 6M, 1Y, 5Y
        """
        periods = {
            "1D": 1,
            "1W": 7,
            "1M": 30,
            "3M": 90,
            "6M": 180,
            "1Y": 365,
            "5Y": 1825,
        }
        days = periods.get(period.upper(), 30)
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        return await self.get_historical_prices(symbol, from_date, to_date)

    async def get_company_profile(self, symbol: str) -> CompanyProfile:
        """Get company profile and fundamentals."""
        # Stable API: /stable/profile?symbol=AAPL
        params = {"symbol": symbol.upper()}
        data = await self._get("/profile", params)
        if not data or (isinstance(data, list) and len(data) == 0):
            raise SymbolNotFoundError(symbol)
        profile_data = data[0] if isinstance(data, list) else data
        return CompanyProfile.model_validate(profile_data)

    async def get_news(
        self, symbol: Optional[str] = None, limit: int = 50
    ) -> list[NewsArticle]:
        """Get news articles, optionally filtered by symbol."""
        # Stable API: /stable/news/stock-latest?page=0&limit=20
        # For symbol-specific: /stable/news/stock?symbols=AAPL (note: plural 'symbols')
        params = {"limit": limit, "page": 0}
        if symbol:
            endpoint = "/news/stock"
            params["symbols"] = symbol.upper()
        else:
            endpoint = "/news/stock-latest"

        data = await self._get(endpoint, params)
        if not data:
            return []
        if isinstance(data, dict):
            # Some endpoints wrap in content key
            data = data.get("content", data) if "content" in data else [data]
        return [NewsArticle.model_validate(item) for item in data]

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for symbols by name or ticker."""
        # Stable API: /stable/search-name works for both names and tickers
        params = {"query": query, "limit": limit}
        data = await self._get("/search-name", params)
        if not data:
            return []
        return [SearchResult.model_validate(item) for item in data]

    async def get_financial_ratios_ttm(self, symbol: str) -> FinancialRatiosTTM:
        """Get trailing twelve month financial ratios for a symbol."""
        params = {"symbol": symbol.upper()}
        data = await self._get("/ratios-ttm", params)
        if not data or (isinstance(data, list) and len(data) == 0):
            raise SymbolNotFoundError(symbol)
        ratios_data = data[0] if isinstance(data, list) else data
        return FinancialRatiosTTM.model_validate(ratios_data)

    async def get_key_metrics_ttm(self, symbol: str) -> KeyMetricsTTM:
        """Get trailing twelve month key metrics for a symbol."""
        params = {"symbol": symbol.upper()}
        data = await self._get("/key-metrics-ttm", params)
        if not data or (isinstance(data, list) and len(data) == 0):
            raise SymbolNotFoundError(symbol)
        metrics_data = data[0] if isinstance(data, list) else data
        return KeyMetricsTTM.model_validate(metrics_data)

    async def get_income_statement(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[IncomeStatement]:
        """Get income statement data for a symbol.

        Args:
            symbol: Stock symbol
            limit: Number of periods to return
            period: 'annual' or 'quarter'
        """
        params = {"symbol": symbol.upper(), "limit": limit, "period": period}
        data = await self._get("/income-statement", params)
        if not data:
            return []
        return [IncomeStatement.model_validate(item) for item in data]

    async def get_balance_sheet(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[BalanceSheet]:
        """Get balance sheet data for a symbol.

        Args:
            symbol: Stock symbol
            limit: Number of periods to return
            period: 'annual' or 'quarter'
        """
        params = {"symbol": symbol.upper(), "limit": limit, "period": period}
        data = await self._get("/balance-sheet-statement", params)
        if not data:
            return []
        return [BalanceSheet.model_validate(item) for item in data]

    async def get_cash_flow_statement(
        self, symbol: str, limit: int = 4, period: str = "annual"
    ) -> list[CashFlowStatement]:
        """Get cash flow statement data for a symbol.

        Args:
            symbol: Stock symbol
            limit: Number of periods to return
            period: 'annual' or 'quarter'
        """
        params = {"symbol": symbol.upper(), "limit": limit, "period": period}
        data = await self._get("/cash-flow-statement", params)
        if not data:
            return []
        return [CashFlowStatement.model_validate(item) for item in data]

    async def get_world_indices(self) -> list[Quote]:
        """Fetch quotes for major world indices."""
        symbols = [
            # US
            "^GSPC", "^DJI", "^IXIC", "^RUT",
            # Europe
            "^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^IBEX", "^AEX",
            # Asia-Pacific
            "^N225", "^HSI", "^KS11", "^AXJO", "^BSESN", "^TWII", "^STI",
        ]
        return await self.get_quotes(symbols)

    async def get_most_active(self, limit: int = 20) -> list[Quote]:
        """Get most active market movers (biggest gainers)."""
        data = await self._get("/biggest-gainers")
        if not data:
            return []
        # Map the response to Quote format
        quotes = []
        for item in data[:limit]:
            quote_data = {
                "symbol": item.get("symbol", ""),
                "name": item.get("name", ""),
                "price": item.get("price", 0),
                "change": item.get("change", 0),
                "changePercentage": item.get("changesPercentage", 0),
                "volume": 0,  # Not provided by this endpoint
                "exchange": item.get("exchange", ""),
            }
            quotes.append(Quote.model_validate(quote_data))
        return quotes

    async def get_treasury_rates(self) -> tuple[dict, dict | None]:
        """Get current US Treasury rates for all maturities.

        Returns:
            Tuple of (current_rates, previous_rates) for calculating changes.
            previous_rates may be None if not available.
        """
        data = await self._get("/treasury-rates")
        if not data:
            return {}, None
        current = data[0] if len(data) > 0 else {}
        previous = data[1] if len(data) > 1 else None
        return current, previous

    async def get_forex_quotes(self) -> list[Quote]:
        """Get quotes for currency ETFs as forex proxy."""
        # Use currency ETFs since direct forex endpoints not available
        # FXE=Euro, FXY=Yen, FXB=Pound, FXC=CAD, FXA=AUD, UUP=USD Index
        symbols = ["FXE", "FXY", "FXB", "FXC", "FXA", "UUP"]
        return await self.get_quotes(symbols)
