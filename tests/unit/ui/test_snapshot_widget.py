"""Unit tests for SnapshotWidget."""

import pytest

from boomberg.api.models import Quote
from boomberg.ui.widgets.snapshot import SnapshotWidget


class TestSnapshotWidget:
    """Tests for SnapshotWidget."""

    @pytest.fixture
    def widget(self):
        """Create a SnapshotWidget for testing."""
        return SnapshotWidget()

    @pytest.fixture
    def sample_indices(self) -> list[Quote]:
        """Create sample index quotes."""
        return [
            Quote(symbol="^GSPC", name="S&P 500", price=5234.18, change=23.45, changePercentage=0.45),
            Quote(symbol="^DJI", name="Dow Jones", price=38654.42, change=123.45, changePercentage=0.32),
            Quote(symbol="^IXIC", name="NASDAQ", price=16428.82, change=109.88, changePercentage=0.67),
            Quote(symbol="^RUT", name="Russell 2000", price=2045.32, change=-3.07, changePercentage=-0.15),
            Quote(symbol="^FTSE", name="FTSE 100", price=8125.45, change=26.00, changePercentage=0.32),
            Quote(symbol="^GDAXI", name="DAX", price=18432.67, change=106.91, changePercentage=0.58),
            Quote(symbol="^N225", name="Nikkei 225", price=38452.12, change=473.16, changePercentage=1.23),
            Quote(symbol="^HSI", name="Hang Seng", price=17845.32, change=-80.30, changePercentage=-0.45),
        ]

    @pytest.fixture
    def sample_commodities(self) -> list[Quote]:
        """Create sample commodity ETF quotes."""
        return [
            Quote(symbol="GLD", name="SPDR Gold Shares", price=185.45, change=0.83, changePercentage=0.45),
            Quote(symbol="USO", name="United States Oil Fund", price=72.30, change=-0.89, changePercentage=-1.23),
            Quote(symbol="SLV", name="iShares Silver Trust", price=22.15, change=0.07, changePercentage=0.32),
        ]

    @pytest.fixture
    def sample_sectors(self) -> list[Quote]:
        """Create sample sector ETF quotes."""
        return [
            Quote(symbol="XLK", name="Technology Select Sector", price=195.42, change=2.31, changePercentage=1.2),
            Quote(symbol="XLF", name="Financial Select Sector", price=42.15, change=0.34, changePercentage=0.8),
            Quote(symbol="XLE", name="Energy Select Sector", price=87.30, change=-0.44, changePercentage=-0.5),
        ]

    @pytest.fixture
    def sample_bonds(self) -> dict:
        """Create sample bond data."""
        return {"year2": 4.25, "year5": 4.15, "year10": 4.28, "year30": 4.45}

    def test_initial_state(self, widget):
        """Test widget initial state."""
        assert widget._indices == []
        assert widget._commodities == []
        assert widget._sectors == []
        assert widget._bonds == {}
        assert widget._last_updated is None

    def test_update_snapshot(self, widget, sample_indices, sample_commodities, sample_sectors, sample_bonds):
        """Test updating snapshot data."""
        widget.update_snapshot(
            indices=sample_indices,
            commodities=sample_commodities,
            sectors=sample_sectors,
            bonds=sample_bonds,
        )

        assert len(widget._indices) == 8
        assert len(widget._commodities) == 3
        assert len(widget._sectors) == 3
        assert widget._bonds == sample_bonds
        assert widget._last_updated is not None

    def test_render_empty(self, widget):
        """Test rendering empty widget."""
        result = widget.render()
        assert "Loading" in str(result)

    def test_render_with_data(self, widget, sample_indices, sample_commodities, sample_sectors, sample_bonds):
        """Test rendering with data."""
        widget.update_snapshot(
            indices=sample_indices,
            commodities=sample_commodities,
            sectors=sample_sectors,
            bonds=sample_bonds,
        )
        result = widget.render()
        # Should return a Panel with content
        assert result is not None

    def test_format_change_positive(self, widget):
        """Test formatting positive change."""
        text = widget._format_change(1.23)
        assert "+1.23%" in str(text)
        assert text.style == "green"

    def test_format_change_negative(self, widget):
        """Test formatting negative change."""
        text = widget._format_change(-0.45)
        assert "-0.45%" in str(text)
        assert text.style == "red"

    def test_format_change_zero(self, widget):
        """Test formatting zero change."""
        text = widget._format_change(0.0)
        assert "+0.00%" in str(text)
        assert text.style == "green"
