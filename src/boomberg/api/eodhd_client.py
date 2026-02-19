"""Async EODHD (End of Day Historical Data) API client for government bonds."""

import asyncio
from typing import Optional

import httpx

from boomberg.config import Settings


# Country bond configurations (excluding US which uses FMP)
COUNTRY_BONDS = {
    "CA": {
        "name": "Canada",
        "maturities": ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y", "20Y", "30Y"],
    },
    "DE": {
        "name": "Germany",
        "maturities": ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y", "30Y"],
    },
    "UK": {
        "name": "United Kingdom",
        "maturities": ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y", "30Y"],
    },
    "JP": {
        "name": "Japan",
        "maturities": ["3M", "2Y", "3Y", "5Y", "10Y", "30Y"],
    },
    "FR": {
        "name": "France",
        "maturities": ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y"],
    },
    "AU": {
        "name": "Australia",
        "maturities": ["1Y", "2Y", "5Y", "10Y", "30Y"],
    },
    "IT": {
        "name": "Italy",
        "maturities": ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "10Y", "30Y"],
    },
    "ES": {
        "name": "Spain",
        "maturities": ["6M", "1Y", "3Y", "5Y", "10Y"],
    },
    "CN": {
        "name": "China",
        "maturities": ["1Y", "2Y", "3Y", "5Y", "7Y", "10Y"],
    },
}


class EODHDClient:
    """Async client for EODHD Government Bonds API."""

    def __init__(self, settings: Settings):
        self._settings = settings
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "EODHDClient":
        self._client = httpx.AsyncClient(
            base_url=self._settings.eodhd_base_url,
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

    def _build_symbol(self, country_code: str, maturity: str) -> str:
        """Build EODHD symbol for a bond.

        Args:
            country_code: Two-letter country code (e.g., 'DE', 'JP')
            maturity: Maturity string (e.g., '10Y', '5Y', '3M')

        Returns:
            EODHD symbol (e.g., 'DE10Y.GBOND')
        """
        return f"{country_code}{maturity}.GBOND"

    async def get_bond_yield(self, symbol: str) -> Optional[dict]:
        """Get real-time yield for a single bond.

        Args:
            symbol: Bond symbol without .GBOND suffix (e.g., 'DE10Y')

        Returns:
            Dictionary with bond data including 'close' (yield), 'change', etc.
            Falls back to 'previousClose' if 'close' is 'NA'.
            Returns None if fetch fails or no valid data.
        """
        try:
            params = {
                "api_token": self._settings.eodhd_api_key,
                "fmt": "json",
            }
            response = await self.client.get(
                f"/real-time/{symbol}.GBOND",
                params=params,
            )
            response.raise_for_status()
            data = response.json()

            # Handle 'NA' values - fall back to previousClose if close is NA
            if data.get("close") == "NA" or data.get("close") is None:
                if data.get("previousClose") and data.get("previousClose") != "NA":
                    data["close"] = data["previousClose"]
                else:
                    return None

            # Convert change to None if NA
            if data.get("change") == "NA":
                data["change"] = None

            return data
        except Exception:
            return None

    async def get_country_yields(self, country_code: str) -> dict[str, dict]:
        """Get all available bond yields for a country.

        Args:
            country_code: Two-letter country code (e.g., 'DE', 'JP')

        Returns:
            Dictionary mapping maturity (e.g., '10Y') to bond data.
            Returns empty dict if country not found.
        """
        country_code = country_code.upper()
        if country_code not in COUNTRY_BONDS:
            return {}

        maturities = COUNTRY_BONDS[country_code]["maturities"]

        async def fetch_maturity(maturity: str) -> tuple[str, Optional[dict]]:
            symbol = f"{country_code}{maturity}"
            data = await self.get_bond_yield(symbol)
            return maturity, data

        results = await asyncio.gather(*[fetch_maturity(m) for m in maturities])

        return {maturity: data for maturity, data in results if data is not None}

    async def get_international_snapshot(self) -> dict[str, dict]:
        """Get 10Y yields for all supported countries.

        Returns:
            Dictionary mapping country code to dict with '10Y' yield.
            Example: {'DE': {'10Y': 2.45}, 'JP': {'10Y': 0.92}}
        """
        snapshot_maturities = ["1M", "5Y", "10Y"]

        async def fetch_country(country_code: str) -> tuple[str, dict]:
            maturities_available = COUNTRY_BONDS[country_code]["maturities"]
            yields = {}

            for mat in snapshot_maturities:
                if mat in maturities_available:
                    symbol = f"{country_code}{mat}"
                    data = await self.get_bond_yield(symbol)
                    if data and "close" in data:
                        yields[mat] = data["close"]

            return country_code, yields

        results = await asyncio.gather(
            *[fetch_country(code) for code in COUNTRY_BONDS.keys()]
        )

        return {code: yields for code, yields in results if yields}
