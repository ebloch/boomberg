"""Unit tests for EODHDClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from boomberg.api.eodhd_client import EODHDClient, COUNTRY_BONDS
from boomberg.config import Settings


class TestEODHDClient:
    """Tests for EODHDClient."""

    @pytest.fixture
    def test_settings(self) -> Settings:
        """Create test settings with EODHD API key."""
        return Settings(
            fmp_api_key="test_fmp_key",
            eodhd_api_key="test_eodhd_key",
            eodhd_base_url="https://eodhd.com/api",
        )

    @pytest.fixture
    def client(self, test_settings):
        """Create EODHDClient with test settings."""
        return EODHDClient(test_settings)

    def test_client_not_initialized(self, client):
        """Test client property raises error when not initialized."""
        with pytest.raises(RuntimeError, match="Client not initialized"):
            _ = client.client

    @pytest.mark.asyncio
    async def test_context_manager_initializes_client(self, client):
        """Test async context manager initializes the client."""
        async with client as c:
            assert c._client is not None

        # Client should be closed after exiting context
        assert client._client is None

    @pytest.mark.asyncio
    async def test_get_bond_yield(self, client):
        """Test fetching single bond yield."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "code": "DE10Y.GBOND",
            "close": 2.45,
            "previousClose": 2.40,
            "change": 0.05,
            "change_p": 2.08,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            result = await client.get_bond_yield("DE10Y")

            assert result is not None
            assert result["close"] == 2.45
            assert result["change"] == 0.05

            mock_client.get.assert_called_once_with(
                "/real-time/DE10Y.GBOND",
                params={"api_token": "test_eodhd_key", "fmt": "json"},
            )

    @pytest.mark.asyncio
    async def test_get_bond_yield_handles_error(self, client):
        """Test bond yield returns None on API error."""
        with patch.object(client, "_client") as mock_client:
            mock_client.get = AsyncMock(side_effect=Exception("API error"))
            client._client = mock_client

            result = await client.get_bond_yield("INVALID")

            assert result is None

    @pytest.mark.asyncio
    async def test_get_country_yields(self, client):
        """Test fetching all bond yields for a country."""
        # Germany has maturities: 3M, 6M, 1Y, 2Y, 3Y, 5Y, 10Y, 30Y
        mock_responses = {
            "DE3M": {"code": "DE3M.GBOND", "close": 2.10},
            "DE6M": {"code": "DE6M.GBOND", "close": 2.15},
            "DE1Y": {"code": "DE1Y.GBOND", "close": 2.20},
            "DE2Y": {"code": "DE2Y.GBOND", "close": 2.25},
            "DE3Y": {"code": "DE3Y.GBOND", "close": 2.30},
            "DE5Y": {"code": "DE5Y.GBOND", "close": 2.35},
            "DE10Y": {"code": "DE10Y.GBOND", "close": 2.45},
            "DE30Y": {"code": "DE30Y.GBOND", "close": 2.60},
        }

        async def mock_get(endpoint, params):
            # Extract symbol from endpoint like /real-time/DE10Y.GBOND
            symbol = endpoint.replace("/real-time/", "").replace(".GBOND", "")
            resp = MagicMock()
            resp.json.return_value = mock_responses.get(symbol, {})
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(client, "_client") as mock_client:
            mock_client.get = mock_get
            client._client = mock_client

            result = await client.get_country_yields("DE")

            assert "10Y" in result
            assert result["10Y"]["close"] == 2.45
            assert "5Y" in result
            assert result["5Y"]["close"] == 2.35

    @pytest.mark.asyncio
    async def test_get_country_yields_unknown_country(self, client):
        """Test country yields returns empty dict for unknown country."""
        with patch.object(client, "_client") as mock_client:
            client._client = mock_client

            result = await client.get_country_yields("XX")

            assert result == {}

    @pytest.mark.asyncio
    async def test_get_international_snapshot(self, client):
        """Test fetching international bond snapshot (10Y for all countries)."""
        mock_responses = {
            "CA10Y": {"code": "CA10Y.GBOND", "close": 3.42},
            "DE10Y": {"code": "DE10Y.GBOND", "close": 2.45},
            "UK10Y": {"code": "UK10Y.GBOND", "close": 4.15},
            "JP10Y": {"code": "JP10Y.GBOND", "close": 0.92},
            "FR10Y": {"code": "FR10Y.GBOND", "close": 3.12},
            "AU10Y": {"code": "AU10Y.GBOND", "close": 4.05},
        }

        async def mock_get(endpoint, params):
            symbol = endpoint.replace("/real-time/", "").replace(".GBOND", "")
            resp = MagicMock()
            if symbol in mock_responses:
                resp.json.return_value = mock_responses[symbol]
            else:
                resp.json.return_value = {}
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(client, "_client") as mock_client:
            mock_client.get = mock_get
            client._client = mock_client

            result = await client.get_international_snapshot()

            assert "DE" in result
            assert result["DE"]["10Y"] == 2.45
            assert "JP" in result
            assert result["JP"]["10Y"] == 0.92

    def test_country_bonds_constant(self):
        """Test COUNTRY_BONDS constant has expected structure."""
        assert "DE" in COUNTRY_BONDS
        assert "10Y" in COUNTRY_BONDS["DE"]["maturities"]
        assert "name" in COUNTRY_BONDS["DE"]
        assert COUNTRY_BONDS["DE"]["name"] == "Germany"

        # Check US is not in COUNTRY_BONDS (use FMP for US)
        assert "US" not in COUNTRY_BONDS

    def test_build_symbol(self, client):
        """Test building EODHD bond symbol."""
        assert client._build_symbol("DE", "10Y") == "DE10Y.GBOND"
        assert client._build_symbol("JP", "5Y") == "JP5Y.GBOND"
        assert client._build_symbol("CA", "1M") == "CA1M.GBOND"
