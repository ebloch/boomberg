"""Async FRED (Federal Reserve Economic Data) API client."""

from typing import Optional

import httpx

from boomberg.config import Settings


class FREDClient:
    """Async client for Federal Reserve Economic Data API."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "FREDClient":
        self._client = httpx.AsyncClient(
            base_url=self._settings.fred_base_url,
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

    async def get_series(self, series_id: str, limit: int = 1) -> list[dict]:
        """Get observations for a FRED series.

        Args:
            series_id: FRED series identifier (e.g., 'GDP', 'UNRATE')
            limit: Number of observations to return

        Returns:
            List of observation dictionaries with 'date' and 'value' keys
        """
        params = {
            "series_id": series_id,
            "api_key": self._settings.fred_api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        }
        response = await self.client.get("/series/observations", params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("observations", [])

    async def get_economic_indicators(self) -> dict:
        """Get key economic indicators.

        Returns:
            Dictionary mapping indicator names to their latest observations
        """
        series = {
            "GDP": "GDP",
            "Unemployment": "UNRATE",
            "CPI": "CPIAUCSL",
            "Fed Funds Rate": "FEDFUNDS",
            "10Y Treasury": "DGS10",
        }
        results = {}
        for name, series_id in series.items():
            try:
                obs = await self.get_series(series_id, limit=1)
                if obs:
                    results[name] = obs[0]
            except Exception:
                results[name] = None
        return results
