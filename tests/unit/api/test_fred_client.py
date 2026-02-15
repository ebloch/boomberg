"""Unit tests for FREDClient."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from boomberg.api.fred_client import FREDClient
from boomberg.config import Settings


class TestFREDClient:
    """Tests for FREDClient."""

    @pytest.fixture
    def test_settings(self) -> Settings:
        """Create test settings with FRED API key."""
        return Settings(
            fmp_api_key="test_fmp_key",
            fred_api_key="test_fred_key",
            fred_base_url="https://api.stlouisfed.org/fred",
        )

    @pytest.fixture
    def client(self, test_settings):
        """Create FREDClient with test settings."""
        return FREDClient(test_settings)

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
    async def test_get_series(self, client, test_settings):
        """Test fetching FRED series observations."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "observations": [
                {"date": "2025-01-01", "value": "3.7"},
                {"date": "2024-12-01", "value": "3.8"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            result = await client.get_series("UNRATE", limit=2)

            assert len(result) == 2
            assert result[0]["date"] == "2025-01-01"
            assert result[0]["value"] == "3.7"

            mock_client.get.assert_called_once_with(
                "/series/observations",
                params={
                    "series_id": "UNRATE",
                    "api_key": "test_fred_key",
                    "file_type": "json",
                    "sort_order": "desc",
                    "limit": 2,
                },
            )

    @pytest.mark.asyncio
    async def test_get_economic_indicators(self, client):
        """Test fetching economic indicators."""
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()

        # Set up responses for each indicator
        responses = {
            "GDP": {"observations": [{"date": "2024-10-01", "value": "27963.5"}]},
            "UNRATE": {"observations": [{"date": "2025-01-01", "value": "3.7"}]},
            "CPIAUCSL": {"observations": [{"date": "2025-01-01", "value": "315.6"}]},
            "FEDFUNDS": {"observations": [{"date": "2025-01-01", "value": "5.33"}]},
            "DGS10": {"observations": [{"date": "2025-01-15", "value": "4.28"}]},
        }

        call_count = [0]

        async def mock_get(endpoint, params):
            series_id = params["series_id"]
            resp = MagicMock()
            resp.json.return_value = responses.get(series_id, {"observations": []})
            resp.raise_for_status = MagicMock()
            call_count[0] += 1
            return resp

        with patch.object(client, "_client") as mock_client:
            mock_client.get = mock_get
            client._client = mock_client

            result = await client.get_economic_indicators()

            assert "GDP" in result
            assert "Unemployment" in result
            assert "CPI" in result
            assert "Fed Funds Rate" in result
            assert "10Y Treasury" in result

            assert result["GDP"]["value"] == "27963.5"
            assert result["Unemployment"]["value"] == "3.7"

    @pytest.mark.asyncio
    async def test_get_economic_indicators_handles_errors(self, client):
        """Test economic indicators handles individual series errors gracefully."""
        async def mock_get(endpoint, params):
            series_id = params["series_id"]
            if series_id == "GDP":
                raise Exception("API error")
            resp = MagicMock()
            resp.json.return_value = {"observations": [{"date": "2025-01-01", "value": "3.7"}]}
            resp.raise_for_status = MagicMock()
            return resp

        with patch.object(client, "_client") as mock_client:
            mock_client.get = mock_get
            client._client = mock_client

            result = await client.get_economic_indicators()

            # GDP should be None due to error
            assert result["GDP"] is None
            # Others should have values
            assert result["Unemployment"] is not None

    @pytest.mark.asyncio
    async def test_get_series_empty_response(self, client):
        """Test handling empty observations response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"observations": []}
        mock_response.raise_for_status = MagicMock()

        with patch.object(client, "_client") as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)
            client._client = mock_client

            result = await client.get_series("UNKNOWN", limit=1)

            assert result == []
