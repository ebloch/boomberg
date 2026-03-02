"""Tests for Kalshi API models."""

import pytest

from boomberg.api.kalshi_models import KalshiMarket


class TestKalshiMarket:
    """Tests for KalshiMarket model."""

    def test_market_from_api_response(self):
        """Test parsing a market from API response."""
        api_response = {
            "ticker": "FED-25MAR-T4.75",
            "title": "Will the Fed cut rates in March 2025?",
            "yes_bid": 62,
            "no_bid": 36,
            "last_price": 63,
            "previous_price": 60,
            "volume_24h": 125400,
            "status": "active",
            "close_time": "2025-03-15T16:00:00Z",
            "open_interest": 450200,
        }
        market = KalshiMarket.model_validate(api_response)

        assert market.ticker == "FED-25MAR-T4.75"
        assert market.title == "Will the Fed cut rates in March 2025?"
        assert market.yes_bid == 62
        assert market.no_bid == 36
        assert market.last_price == 63
        assert market.previous_price == 60
        assert market.volume_24h == 125400
        assert market.status == "active"
        assert market.close_time == "2025-03-15T16:00:00Z"
        assert market.open_interest == 450200

    def test_market_with_optional_fields_missing(self):
        """Test parsing a market with minimal fields."""
        api_response = {
            "ticker": "BTC-100K-EOY",
            "title": "Will BTC hit 100K by EOY?",
            "status": "active",
        }
        market = KalshiMarket.model_validate(api_response)

        assert market.ticker == "BTC-100K-EOY"
        assert market.title == "Will BTC hit 100K by EOY?"
        assert market.status == "active"
        assert market.yes_bid is None
        assert market.no_bid is None
        assert market.last_price is None
        assert market.volume_24h == 0

    def test_market_yes_price_dollars(self):
        """Test that yes_price_dollars returns cents as dollars."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            yes_bid=62,
        )
        assert market.yes_price_dollars == 0.62

    def test_market_no_price_dollars(self):
        """Test that no_price_dollars returns cents as dollars."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            no_bid=38,
        )
        assert market.no_price_dollars == 0.38

    def test_market_last_price_dollars(self):
        """Test that last_price_dollars returns cents as dollars."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            last_price=63,
        )
        assert market.last_price_dollars == 0.63

    def test_market_change_cents(self):
        """Test calculating price change in cents."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            last_price=63,
            previous_price=60,
        )
        assert market.change_cents == 3

    def test_market_change_cents_negative(self):
        """Test calculating negative price change."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            last_price=55,
            previous_price=60,
        )
        assert market.change_cents == -5

    def test_market_change_cents_with_missing_prices(self):
        """Test change is 0 when prices are missing."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
        )
        assert market.change_cents == 0

    def test_market_price_dollars_none_when_bid_missing(self):
        """Test price returns None when bid is missing."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
        )
        assert market.yes_price_dollars is None
        assert market.no_price_dollars is None
        assert market.last_price_dollars is None

    def test_market_with_series_ticker(self):
        """Test market can store series_ticker."""
        market = KalshiMarket(
            ticker="FED-25MAR",
            title="Test",
            status="active",
            series_ticker="KXFED",
        )
        assert market.series_ticker == "KXFED"

    def test_market_series_ticker_defaults_to_none(self):
        """Test series_ticker defaults to None."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test",
            status="active",
        )
        assert market.series_ticker is None
