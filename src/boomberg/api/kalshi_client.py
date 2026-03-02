"""Async Kalshi API client."""

import asyncio
from typing import Optional

import httpx

from boomberg.api.exceptions import APIError
from boomberg.api.kalshi_models import KalshiMarket


class KalshiClient:
    """Async client for Kalshi Prediction Markets API (public, read-only)."""

    BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "KalshiClient":
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
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

    async def _get(self, endpoint: str, params: dict | None = None) -> dict:
        """Make GET request to API."""
        response = await self.client.get(endpoint, params=params or {})

        if response.status_code >= 400:
            raise APIError(f"Kalshi API request failed: {response.text}", response.status_code)

        return response.json()

    async def get_events(self, limit: int = 50) -> list[dict]:
        """Get list of events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dictionaries
        """
        data = await self._get("/events", {"limit": limit})
        return data.get("events", [])

    async def get_markets_for_event(self, event_ticker: str) -> list[KalshiMarket]:
        """Get markets for a specific event.

        Args:
            event_ticker: Event ticker

        Returns:
            List of KalshiMarket objects
        """
        data = await self._get("/markets", {"event_ticker": event_ticker})
        markets_data = data.get("markets", [])
        return [KalshiMarket.model_validate(m) for m in markets_data]

    async def get_markets(
        self,
        limit: int = 100,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
    ) -> list[KalshiMarket]:
        """Get list of prediction markets from events.

        This fetches events and then retrieves markets for each event,
        which gives better quality markets than the default /markets endpoint.

        Args:
            limit: Maximum number of markets to return (default 100)
            status: Filter by status (not currently used - API doesn't support it well)
            series_ticker: Filter by series ticker

        Returns:
            List of KalshiMarket objects
        """
        # Get events first
        events = await self.get_events(limit=50)

        # Fetch markets for each event in parallel
        async def fetch_event_markets(event: dict) -> list[KalshiMarket]:
            event_ticker = event.get("event_ticker")
            if not event_ticker:
                return []
            try:
                return await self.get_markets_for_event(event_ticker)
            except APIError:
                return []

        tasks = [fetch_event_markets(e) for e in events[:30]]  # Limit to 30 events
        results = await asyncio.gather(*tasks)

        # Flatten and dedupe by ticker
        all_markets = []
        seen_tickers = set()
        for markets in results:
            for market in markets:
                if market.ticker not in seen_tickers:
                    seen_tickers.add(market.ticker)
                    all_markets.append(market)

        return all_markets[:limit]

    async def get_markets_by_series(self, series_ticker: str) -> list[KalshiMarket]:
        """Get markets for a specific series.

        Args:
            series_ticker: Series ticker (e.g., "KXFED", "KXCPI")

        Returns:
            List of KalshiMarket objects for the series
        """
        data = await self._get("/markets", {"series_ticker": series_ticker})
        return [KalshiMarket.model_validate(m) for m in data.get("markets", [])]

    async def get_market(self, ticker: str) -> KalshiMarket:
        """Get a single market by ticker.

        Args:
            ticker: Market ticker (e.g., "FED-25MAR-T4.75")

        Returns:
            KalshiMarket object
        """
        data = await self._get(f"/markets/{ticker}")
        market_data = data.get("market", data)
        return KalshiMarket.model_validate(market_data)
