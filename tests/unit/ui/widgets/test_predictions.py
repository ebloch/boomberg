"""Unit tests for PredictionWidget."""

import pytest
from io import StringIO
from rich.console import Console

from boomberg.api.kalshi_models import KalshiMarket
from boomberg.ui.widgets.predictions import PredictionWidget


class TestPredictionWidget:
    """Tests for PredictionWidget."""

    @pytest.fixture
    def widget(self):
        """Create a PredictionWidget for testing."""
        return PredictionWidget()

    def _render_to_string(self, widget) -> str:
        """Render widget to string for testing."""
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        return console.file.getvalue()

    @pytest.fixture
    def sample_market(self) -> KalshiMarket:
        """Create a sample market."""
        return KalshiMarket(
            ticker="FED-25MAR-T4.75",
            title="Will the Fed cut rates in March 2025?",
            status="active",
            yes_bid=62,
            no_bid=36,
            yes_ask=64,
            no_ask=38,
            last_price=63,
            previous_price=60,
            volume_24h=125400,
            open_interest=450200,
            close_time="2025-03-15T16:00:00Z",
        )

    @pytest.fixture
    def sample_markets(self, sample_market) -> list[KalshiMarket]:
        """Create sample markets list."""
        market2 = KalshiMarket(
            ticker="BTC-100K-EOY",
            title="Will BTC hit $100K by EOY?",
            status="active",
            yes_bid=45,
            no_bid=53,
            last_price=45,
            previous_price=47,
            volume_24h=89200,
        )
        return [sample_market, market2]

    def test_render_loading_state(self, widget):
        """Test widget shows loading state when no data."""
        output = self._render_to_string(widget)
        assert "Loading" in output

    def test_update_markets_refreshes_widget(self, widget, sample_markets):
        """Test that update_markets updates internal state."""
        widget.update_markets(sample_markets)

        assert widget._markets is not None
        assert len(widget._markets) == 2
        assert widget._detail is None

    def test_update_detail_refreshes_widget(self, widget, sample_market):
        """Test that update_detail updates internal state."""
        widget.update_detail(sample_market)

        assert widget._detail is not None
        assert widget._detail.ticker == "FED-25MAR-T4.75"
        assert widget._markets is None

    def test_render_markets_overview(self, widget, sample_markets):
        """Test rendering markets overview."""
        widget.update_markets(sample_markets)
        output = self._render_to_string(widget)

        # Check that market data is displayed
        assert "Fed cut rates" in output or "Fed" in output
        assert "62c" in output  # Yes bid
        assert "36c" in output  # No bid
        assert "+3c" in output  # Change

    def test_render_market_detail(self, widget, sample_market):
        """Test rendering market detail."""
        widget.update_detail(sample_market)
        output = self._render_to_string(widget)

        # Check that market detail is displayed
        assert "Fed cut rates" in output or "Fed" in output
        assert "FED-25MAR-T4.75" in output  # Ticker
        assert "62c" in output or "64c" in output  # Yes bid or ask
        assert "125.4K" in output  # Volume

    def test_render_positive_change_styled(self, widget, sample_market):
        """Test that positive change shows correctly."""
        widget.update_detail(sample_market)
        output = self._render_to_string(widget)

        # Should show positive change
        assert "+3c" in output

    def test_render_negative_change_styled(self, widget):
        """Test that negative change shows correctly."""
        market = KalshiMarket(
            ticker="TEST",
            title="Test Market",
            status="active",
            yes_bid=45,
            no_bid=53,
            last_price=45,
            previous_price=47,
            volume_24h=1000,
        )
        widget.update_detail(market)
        output = self._render_to_string(widget)

        # Should show negative change
        assert "-2c" in output

    def test_render_volume_formatting(self, widget, sample_markets):
        """Test volume is formatted correctly."""
        widget.update_markets(sample_markets)
        output = self._render_to_string(widget)

        # Volume should be formatted
        assert "125.4K" in output or "89.2K" in output

    def test_widget_clears_detail_on_update_markets(self, widget, sample_market, sample_markets):
        """Test that updating markets clears detail view."""
        widget.update_detail(sample_market)
        assert widget._detail is not None

        widget.update_markets(sample_markets)
        assert widget._detail is None
        assert widget._markets is not None

    def test_widget_clears_markets_on_update_detail(self, widget, sample_market, sample_markets):
        """Test that updating detail clears markets view."""
        widget.update_markets(sample_markets)
        assert widget._markets is not None

        widget.update_detail(sample_market)
        assert widget._markets is None
        assert widget._detail is not None

    def test_render_markets_shows_category_headers(self, widget):
        """Test that markets are rendered with category headers."""
        markets = [
            KalshiMarket(
                ticker="FED-1",
                title="Fed Rate Hike",
                status="active",
                series_ticker="KXFED",
                volume_24h=1000,
                yes_bid=50,
                no_bid=48,
            ),
            KalshiMarket(
                ticker="CPI-1",
                title="CPI Above 2%",
                status="active",
                series_ticker="KXCPI",
                volume_24h=500,
                yes_bid=60,
                no_bid=38,
            ),
        ]
        widget.update_markets(markets)
        output = self._render_to_string(widget)

        # Should show category headers
        assert "Fed Rates" in output
        assert "Inflation" in output

    def test_render_markets_grouped_by_category(self, widget):
        """Test that markets in the same category are grouped together."""
        markets = [
            KalshiMarket(
                ticker="FED-1",
                title="Fed Rate Hike 0bp",
                status="active",
                series_ticker="KXFED",
                volume_24h=1000,
                yes_bid=95,
                no_bid=4,
            ),
            KalshiMarket(
                ticker="CPI-1",
                title="CPI Above 2.5%",
                status="active",
                series_ticker="KXCPI",
                volume_24h=500,
                yes_bid=51,
                no_bid=48,
            ),
            KalshiMarket(
                ticker="FED-2",
                title="Fed Rate Cut 25bp",
                status="active",
                series_ticker="KXFED",
                volume_24h=900,
                yes_bid=3,
                no_bid=96,
            ),
        ]
        widget.update_markets(markets)
        output = self._render_to_string(widget)

        # Both Fed markets should appear after "Fed Rates" header
        fed_rates_pos = output.find("Fed Rates")
        inflation_pos = output.find("Inflation")

        # Fed markets should be between Fed Rates header and Inflation header
        fed1_pos = output.find("Fed Rate Hike")
        fed2_pos = output.find("Fed Rate Cut")

        assert fed_rates_pos < fed1_pos < inflation_pos
        assert fed_rates_pos < fed2_pos < inflation_pos

    def test_shorten_title_removes_fed_prefix(self, widget):
        """Test title shortening removes Federal Reserve prefix."""
        title = "Will the Federal Reserve Hike rates by 25bp in March 2026?"
        short = widget._shorten_title(title, "KXFED")
        assert "Will the Federal Reserve" not in short
        assert "Hike" in short

    def test_shorten_title_removes_cpi_prefix(self, widget):
        """Test title shortening removes CPI prefix."""
        title = "Will CPI inflation be above 2.5% in February?"
        short = widget._shorten_title(title, "KXCPI")
        assert "Will CPI" not in short
        assert "inflation" in short or "above" in short

    def test_shorten_title_no_series_keeps_original(self, widget):
        """Test title is kept when no series_ticker."""
        title = "Some other market title"
        short = widget._shorten_title(title, None)
        assert short == title

    def test_shorten_title_extracts_date_info(self, widget):
        """Test title retains date information when present."""
        title = "Will the Federal Reserve Cut rates by 25bp in March 2026?"
        short = widget._shorten_title(title, "KXFED")
        # Should include the date context
        assert "Mar" in short or "March" in short

    def test_shorten_title_removes_at_their_meeting(self, widget):
        """Test Fed titles remove 'at their meeting' filler."""
        title = "Hike rates by 0bps at their meeting in March 2026?"
        short = widget._shorten_title(title, "KXFED")
        assert "at their meeting" not in short
        assert "Hike" in short
        assert "0bp" in short or "0bps" in short
        assert "Mar" in short

    def test_shorten_title_simplifies_rates_by(self, widget):
        """Test Fed titles simplify 'rates by' to just the amount."""
        title = "Hike rates by 25bps at their meeting in March 2026?"
        short = widget._shorten_title(title, "KXFED")
        assert "rates by" not in short
        assert "25bp" in short or "Hike 25bp" in short

    def test_shorten_title_removes_cpi_rate_prefix(self, widget):
        """Test CPI titles remove 'Will the rate of CPI inflation be' prefix."""
        title = "Will the rate of CPI inflation be above 2.5% in February?"
        short = widget._shorten_title(title, "KXCPI")
        assert "Will the rate of" not in short
        assert "2.5%" in short

    def test_shorten_title_cleans_employment_format(self, widget):
        """Test Employment titles clean up U-3 format."""
        title = "Will the unemployment rate (U-3) be above 4.4% in February?"
        short = widget._shorten_title(title, "KXU3")
        assert "U-3" in short
        assert "4.4%" in short
        assert "Will the unemployment rate" not in short
        # Should simplify "Rate (U-3) be" to "U-3 " for cleaner display
        assert "Rate (U-3) be" not in short

    def test_shorten_title_fed_decision_actual_format(self, widget):
        """Test Fed decision titles with actual Kalshi format.

        Actual format: 'Will the Federal Reserve Hike rates by 0bps at their January 2028 meeting?'
        The date (January 2028) is between 'their' and 'meeting'.
        """
        title = "Will the Federal Reserve Hike rates by 0bps at their March 2026 meeting?"
        short = widget._shorten_title(title, "KXFEDDECISION")
        assert "at their" not in short
        assert "meeting" not in short
        assert "Hike" in short
        assert "0bp" in short
        assert "Mar" in short
        assert "2026" in short

    def test_shorten_title_cpi_yoy_actual_format(self, widget):
        """Test CPI YOY titles with actual Kalshi format.

        Actual format: 'Will the rate of CPI inflation be above 2.4% for the year ending in March 2026?'
        Should remove 'for the year ending' as filler.
        """
        title = "Will the rate of CPI inflation be above 2.4% for the year ending in March 2026?"
        short = widget._shorten_title(title, "KXCPIYOY")
        assert "for the year ending" not in short
        assert "Will the rate of" not in short
        assert "2.4%" in short
        assert "Mar" in short

    def test_render_markets_no_wrap(self, widget):
        """Test that market titles do not wrap to multiple lines."""
        # Create market with a long title
        markets = [
            KalshiMarket(
                ticker="FED-1",
                title="Will the Federal Reserve Hike rates by 0bps at their meeting in March 2026?",
                status="active",
                series_ticker="KXFED",
                volume_24h=1000,
                yes_bid=95,
                no_bid=4,
            ),
        ]
        widget.update_markets(markets)
        output = self._render_to_string(widget)

        # Count newlines - should only have expected structure, not extra from wrapping
        # The title row should be on one line (no mid-title line breaks)
        lines = output.split('\n')
        # Find the line with "Hike" - it should contain the full shortened title
        hike_lines = [l for l in lines if "Hike" in l]
        assert len(hike_lines) == 1  # Only one line should contain "Hike"

    def test_render_markets_category_as_column_header(self, widget):
        """Test that category name appears as the first column header, not separate line."""
        markets = [
            KalshiMarket(
                ticker="FED-1",
                title="Fed Rate Hike",
                status="active",
                series_ticker="KXFED",
                volume_24h=1000,
                yes_bid=50,
                no_bid=48,
            ),
        ]
        widget.update_markets(markets)
        output = self._render_to_string(widget)

        # The category "Fed Rates" should be on the same line as "Yes", "No", etc.
        lines = output.split('\n')
        header_line = next((l for l in lines if "Fed Rates" in l), None)
        assert header_line is not None
        assert "Yes" in header_line  # Yes should be on same line as Fed Rates
        assert "No" in header_line
        assert "1D" in header_line
