"""Tests for API models."""

from datetime import date

import pytest

from boomberg.api.models import HistoricalPrice, Quote


class TestQuote:
    """Tests for Quote model."""

    def test_quote_accepts_float_volume(self):
        """Test that Quote model accepts float values for volume."""
        # This simulates what FMP API actually returns
        quote = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=175.50,
            volume=1194373.62708,  # Float volume from API
        )
        assert quote.volume == 1194373.62708

    def test_quote_accepts_int_volume(self):
        """Test that Quote model still accepts int values for volume."""
        quote = Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=175.50,
            volume=1000000,
        )
        assert quote.volume == 1000000


class TestHistoricalPrice:
    """Tests for HistoricalPrice model."""

    def test_historical_price_accepts_float_volume(self):
        """Test that HistoricalPrice model accepts float values for volume."""
        price = HistoricalPrice(
            date=date(2024, 1, 15),
            open=175.0,
            high=176.0,
            low=174.0,
            close=175.50,
            volume=147793.42357,  # Float volume from API
        )
        assert price.volume == 147793.42357

    def test_historical_price_accepts_int_volume(self):
        """Test that HistoricalPrice model still accepts int values for volume."""
        price = HistoricalPrice(
            date=date(2024, 1, 15),
            open=175.0,
            high=176.0,
            low=174.0,
            close=175.50,
            volume=1000000,
        )
        assert price.volume == 1000000
