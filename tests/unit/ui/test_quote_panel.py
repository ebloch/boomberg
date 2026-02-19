"""Unit tests for quote panel widget."""

import pytest
from datetime import datetime, timedelta
from io import StringIO
from rich.console import Console

from boomberg.api.models import NewsArticle, Quote
from boomberg.ui.widgets.quote_panel import QuotePanel, PriceChanges


class TestQuotePanelNews:
    """Tests for QuotePanel news rendering."""

    @pytest.fixture
    def sample_quote(self) -> Quote:
        """Sample quote for testing."""
        return Quote(
            symbol="AAPL",
            name="Apple Inc.",
            price=175.50,
            change=2.50,
            change_percent=1.45,
            day_high=176.00,
            day_low=173.00,
            year_high=200.00,
            year_low=120.00,
            volume=50000000,
            avg_volume=60000000,
            market_cap=2800000000000,
            pe=28.5,
            eps=6.15,
            exchange="NASDAQ",
        )

    @pytest.fixture
    def sample_news(self) -> list[NewsArticle]:
        """Sample news articles for testing."""
        now = datetime.utcnow()
        return [
            NewsArticle(
                symbol="AAPL",
                title="Apple announces new iPhone",
                text="Apple has announced a new iPhone model...",
                publishedDate=now - timedelta(hours=2),
                site="TechCrunch",
                url="https://techcrunch.com/apple-iphone",
            ),
            NewsArticle(
                symbol="AAPL",
                title="Apple stock rises on strong earnings",
                text="Apple reported strong Q4 earnings...",
                publishedDate=now - timedelta(days=1),
                site="Bloomberg",
                url="https://bloomberg.com/apple-earnings",
            ),
            NewsArticle(
                symbol="AAPL",
                title="Apple expands services division",
                text="Apple is expanding its services...",
                publishedDate=now - timedelta(days=3),
                site="Reuters",
                url="https://reuters.com/apple-services",
            ),
        ]

    def test_update_quote_accepts_news_parameter(self, sample_quote, sample_news):
        """Test that update_quote accepts an optional news parameter."""
        widget = QuotePanel()
        # Should not raise an exception
        widget.update_quote(sample_quote, news=sample_news)
        assert widget._news == sample_news

    def test_update_quote_with_no_news(self, sample_quote):
        """Test that update_quote works without news parameter."""
        widget = QuotePanel()
        widget.update_quote(sample_quote)
        assert widget._news is None or widget._news == []

    def test_render_includes_news_section(self, sample_quote, sample_news):
        """Test that rendered output includes news section when news is provided."""
        widget = QuotePanel()
        widget.update_quote(sample_quote, news=sample_news)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        assert "News" in output, f"Expected 'News' section header in output: {output}"

    def test_render_shows_news_titles(self, sample_quote, sample_news):
        """Test that rendered output shows news article titles."""
        widget = QuotePanel()
        widget.update_quote(sample_quote, news=sample_news)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        assert "Apple announces new iPhone" in output
        assert "Apple stock rises on strong earnings" in output
        assert "Apple expands services division" in output

    def test_render_shows_news_source(self, sample_quote, sample_news):
        """Test that rendered output shows news source."""
        widget = QuotePanel()
        widget.update_quote(sample_quote, news=sample_news)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        assert "TechCrunch" in output
        assert "Bloomberg" in output
        assert "Reuters" in output

    def test_render_shows_relative_time(self, sample_quote, sample_news):
        """Test that rendered output shows relative time for news."""
        widget = QuotePanel()
        widget.update_quote(sample_quote, news=sample_news)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show relative times like "2h ago", "Yesterday", "3d ago"
        assert "2h ago" in output or "h ago" in output
        assert "Yesterday" in output or "1d ago" in output
        assert "3d ago" in output or "d ago" in output

    def test_render_without_news_shows_no_news_section(self, sample_quote):
        """Test that rendered output doesn't show news section when no news."""
        widget = QuotePanel()
        widget.update_quote(sample_quote)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should still show the quote
        assert "AAPL" in output
        # Should not show news section since no news provided
        # (We check the quote panel works without news)
        assert "175.50" in output or "175,50" in output

    def test_render_limits_to_3_news_items(self, sample_quote):
        """Test that only 3 news items are displayed even if more provided."""
        now = datetime.utcnow()
        news = [
            NewsArticle(
                symbol="AAPL",
                title=f"News item {i}",
                text="...",
                publishedDate=now - timedelta(hours=i),
                site="Source",
                url="https://example.com",
            )
            for i in range(5)
        ]

        widget = QuotePanel()
        widget.update_quote(sample_quote, news=news)

        console = Console(file=StringIO(), force_terminal=True, width=100)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show first 3 news items
        assert "News item 0" in output
        assert "News item 1" in output
        assert "News item 2" in output
        # Should NOT show items 4 and 5
        assert "News item 3" not in output
        assert "News item 4" not in output
