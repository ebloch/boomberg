"""Unit tests for portfolio widget."""

import pytest
from rich.console import Console
from io import StringIO

from boomberg.services.portfolio import PortfolioHolding
from boomberg.ui.widgets.portfolio import PortfolioWidget


class TestPortfolioWidget:
    """Tests for PortfolioWidget."""

    @pytest.fixture
    def sample_holding(self) -> PortfolioHolding:
        """Sample holding for testing."""
        return PortfolioHolding(
            symbol="AAPL",
            name="Apple Inc.",
            shares=100,
            cost_basis=150.00,  # Per-share cost
            current_price=175.00,
            total_value=17500.00,
            total_cost=15000.00,
            gain_loss=2500.00,
            gain_loss_percent=16.67,
            change_1d_value=250.00,
            change_1d_pct=1.45,
            change_mtd_value=500.00,
            change_mtd_pct=2.94,
            change_ytd_value=1000.00,
            change_ytd_pct=6.06,
            exchange="NASDAQ",
        )

    def test_portfolio_shows_cost_column_not_price(self, sample_holding):
        """Test that portfolio displays Cost column header, not Price."""
        widget = PortfolioWidget()
        widget._holdings = [sample_holding]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show "Cost" column, not "Price"
        assert "Cost" in output, f"Expected 'Cost' column header in output: {output}"
        assert "Price" not in output, f"Did not expect 'Price' column header in output: {output}"

    def test_portfolio_shows_total_cost_value(self, sample_holding):
        """Test that portfolio displays the total cost of the position."""
        widget = PortfolioWidget()
        widget._holdings = [sample_holding]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show total_cost ($15,000), not per-share cost_basis ($150.00)
        assert "15,000" in output, f"Expected total_cost '15,000' in output: {output}"

    def test_gain_loss_shows_only_percent(self, sample_holding):
        """Test that gain/loss column shows only percentage, not dollar value."""
        widget = PortfolioWidget()
        widget._holdings = [sample_holding]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show percentage (+16.7%)
        assert "16.7%" in output, f"Expected gain/loss percent '16.7%' in output: {output}"
        # Should NOT show dollar value ($2,500)
        assert "2,500" not in output, f"Did not expect gain/loss dollar value '2,500' in output: {output}"

    def test_fractional_shares_display(self):
        """Test that fractional shares are displayed correctly, not rounded to integers."""
        holding = PortfolioHolding(
            symbol="BTCUSD",
            name="Bitcoin",
            shares=1.56,  # Fractional shares
            cost_basis=50000.00,
            current_price=52000.00,
            total_value=81120.00,  # 1.56 * 52000
            total_cost=78000.00,  # 1.56 * 50000
            gain_loss=3120.00,
            gain_loss_percent=4.0,
            change_1d_value=156.00,
            change_1d_pct=0.19,
            change_mtd_value=500.00,
            change_mtd_pct=0.62,
            change_ytd_value=1000.00,
            change_ytd_pct=1.25,
            exchange="CRYPTO",
        )
        widget = PortfolioWidget()
        widget._holdings = [holding]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should show fractional shares (1.56), not rounded (2)
        assert "1.56" in output, f"Expected fractional shares '1.56' in output: {output}"

    def test_no_total_row(self, sample_holding):
        """Test that portfolio does not show a TOTAL row."""
        widget = PortfolioWidget()
        widget._holdings = [sample_holding]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # Should NOT show TOTAL row
        assert "TOTAL" not in output, f"Did not expect 'TOTAL' row in output: {output}"

    def test_holdings_sorted_by_value_descending(self):
        """Test that holdings are sorted by total value, highest first."""
        low_value = PortfolioHolding(
            symbol="LOW",
            name="Low Value",
            shares=10,
            cost_basis=10.00,
            current_price=10.00,
            total_value=100.00,  # Lowest
            total_cost=100.00,
            gain_loss=0.0,
            gain_loss_percent=0.0,
            change_1d_value=0.0,
            change_1d_pct=0.0,
            change_mtd_value=0.0,
            change_mtd_pct=0.0,
            change_ytd_value=0.0,
            change_ytd_pct=0.0,
            exchange="NYSE",
        )
        high_value = PortfolioHolding(
            symbol="HIGH",
            name="High Value",
            shares=100,
            cost_basis=100.00,
            current_price=100.00,
            total_value=10000.00,  # Highest
            total_cost=10000.00,
            gain_loss=0.0,
            gain_loss_percent=0.0,
            change_1d_value=0.0,
            change_1d_pct=0.0,
            change_mtd_value=0.0,
            change_mtd_pct=0.0,
            change_ytd_value=0.0,
            change_ytd_pct=0.0,
            exchange="NYSE",
        )
        mid_value = PortfolioHolding(
            symbol="MID",
            name="Mid Value",
            shares=50,
            cost_basis=20.00,
            current_price=20.00,
            total_value=1000.00,  # Middle
            total_cost=1000.00,
            gain_loss=0.0,
            gain_loss_percent=0.0,
            change_1d_value=0.0,
            change_1d_pct=0.0,
            change_mtd_value=0.0,
            change_mtd_pct=0.0,
            change_ytd_value=0.0,
            change_ytd_pct=0.0,
            exchange="NYSE",
        )

        widget = PortfolioWidget()
        # Add in wrong order
        widget._holdings = [low_value, high_value, mid_value]

        # Render to string
        console = Console(file=StringIO(), force_terminal=True, width=120)
        renderable = widget.render()
        console.print(renderable)
        output = console.file.getvalue()

        # HIGH should appear before MID, MID before LOW
        high_pos = output.find("HIGH")
        mid_pos = output.find("MID")
        low_pos = output.find("LOW")

        assert high_pos < mid_pos < low_pos, f"Holdings not sorted by value descending. HIGH={high_pos}, MID={mid_pos}, LOW={low_pos}"
