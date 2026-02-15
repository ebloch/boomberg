"""Unit tests for NewsService."""

from datetime import datetime, timezone, timedelta

import pytest
from unittest.mock import AsyncMock, MagicMock

from boomberg.api.models import NewsArticle
from boomberg.services.news import NewsService


class TestNewsService:
    """Tests for NewsService."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock FMP client."""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_client):
        """Create NewsService with mock client."""
        return NewsService(mock_client)

    @pytest.fixture
    def sample_article(self) -> NewsArticle:
        """Create a sample news article."""
        return NewsArticle(
            symbol="AAPL",
            title="Apple Reports Record Q4 Earnings",
            text="Apple Inc reported record revenue in Q4 with strong iPhone sales.",
            publishedDate=datetime.now(timezone.utc) - timedelta(hours=2),
            site="Bloomberg",
            url="https://example.com/news/1",
        )

    @pytest.mark.asyncio
    async def test_get_news(self, service, mock_client, sample_article):
        """Test fetching news."""
        mock_client.get_news = AsyncMock(return_value=[sample_article])

        result = await service.get_news(symbol="AAPL", limit=10)

        assert len(result) == 1
        assert result[0] == sample_article
        mock_client.get_news.assert_called_once_with("AAPL", 10)

    @pytest.mark.asyncio
    async def test_get_market_news(self, service, mock_client, sample_article):
        """Test fetching market news."""
        mock_client.get_news = AsyncMock(return_value=[sample_article])

        result = await service.get_market_news(limit=50)

        assert len(result) == 1
        mock_client.get_news.assert_called_once_with(limit=50)

    @pytest.mark.asyncio
    async def test_get_symbol_news(self, service, mock_client, sample_article):
        """Test fetching symbol-specific news."""
        mock_client.get_news = AsyncMock(return_value=[sample_article])

        result = await service.get_symbol_news("AAPL", limit=20)

        assert len(result) == 1
        mock_client.get_news.assert_called_once_with(symbol="AAPL", limit=20)

    def test_format_published_date_minutes(self, service):
        """Test formatting recent article (minutes ago)."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime.now(timezone.utc) - timedelta(minutes=15),
        )
        result = service.format_published_date(article)
        assert result == "15m ago"

    def test_format_published_date_just_now(self, service):
        """Test formatting very recent article."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime.now(timezone.utc) - timedelta(seconds=30),
        )
        result = service.format_published_date(article)
        assert result == "Just now"

    def test_format_published_date_hours(self, service):
        """Test formatting article from hours ago."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime.now(timezone.utc) - timedelta(hours=5),
        )
        result = service.format_published_date(article)
        assert result == "5h ago"

    def test_format_published_date_yesterday(self, service):
        """Test formatting article from yesterday."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime.now(timezone.utc) - timedelta(days=1),
        )
        result = service.format_published_date(article)
        assert result == "Yesterday"

    def test_format_published_date_days(self, service):
        """Test formatting article from days ago."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime.now(timezone.utc) - timedelta(days=3),
        )
        result = service.format_published_date(article)
        assert result == "3d ago"

    def test_format_published_date_weeks(self, service):
        """Test formatting article from weeks ago."""
        article = NewsArticle(
            title="Test",
            publishedDate=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        result = service.format_published_date(article)
        assert result == "Jan 15"

    def test_truncate_text_short(self, service):
        """Test truncate doesn't modify short text."""
        text = "Short text."
        assert service.truncate_text(text, 200) == text

    def test_truncate_text_long(self, service):
        """Test truncate properly shortens long text."""
        text = "This is a very long text that should be truncated because it exceeds the maximum length."
        result = service.truncate_text(text, 50)
        assert len(result) <= 50
        assert result.endswith("...")

    def test_truncate_text_preserves_words(self, service):
        """Test truncate doesn't break words."""
        text = "Hello world this is a test of truncation."
        result = service.truncate_text(text, 20)
        # Should break at word boundary
        assert result == "Hello world this..."
