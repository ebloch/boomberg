"""Portfolio widget for displaying holdings and performance."""

from datetime import datetime
from typing import Optional

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from boomberg.services.portfolio import PortfolioHolding
from boomberg.ui.widgets.quote_panel import get_currency_symbol


class PortfolioWidget(Static):
    """Widget for displaying portfolio holdings with performance metrics."""

    DEFAULT_CSS = """
    PortfolioWidget {
        width: 100%;
        height: auto;
        min-height: 10;
        padding: 1;
        background: $surface;
        border: solid $primary;
        border-title-align: center;
        border-title-color: cyan;
        border-title-style: bold;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._holdings: list[PortfolioHolding] = []
        self._empty_message = "Portfolio is empty. Use 'PA <SYMBOL> <SHARES> <TOTAL_COST>' to add holdings."
        self._last_updated: Optional[datetime] = None

    def update_holdings(self, holdings: list[PortfolioHolding]) -> None:
        """Update the displayed holdings."""
        self._holdings = holdings
        self._last_updated = datetime.now()
        self.refresh()

    def set_empty_message(self, message: str) -> None:
        """Set the message shown when portfolio is empty."""
        self._empty_message = message

    def render(self) -> RenderableType:
        """Render the portfolio."""
        self.border_title = "Portfolio"

        if not self._holdings:
            return Text(self._empty_message, style="dim italic")

        table = Table(
            box=None,
            padding=(0, 1),
            expand=True,
            row_styles=["on grey23", ""],
        )

        # Columns
        table.add_column("Symbol", style="bold yellow", width=8)
        table.add_column("Shares", justify="right", width=8)
        table.add_column("Cost", justify="right", width=10)
        table.add_column("Value", justify="right", width=12)
        table.add_column("Gain/Loss", justify="right", width=12)
        table.add_column("1D", justify="right", width=10)
        table.add_column("MTD", justify="right", width=10)
        table.add_column("YTD", justify="right", width=10)

        # Sort holdings by value descending
        sorted_holdings = sorted(self._holdings, key=lambda h: h.total_value, reverse=True)

        for h in sorted_holdings:
            currency = get_currency_symbol(h.exchange)
            gain_style = "green" if h.gain_loss >= 0 else "red"
            d1_style = "green" if h.change_1d_pct >= 0 else "red"
            mtd_style = "green" if h.change_mtd_pct >= 0 else "red"
            ytd_style = "green" if h.change_ytd_pct >= 0 else "red"

            # Format gain/loss (percentage only)
            gain_sign = "+" if h.gain_loss_percent >= 0 else ""
            gain_text = f"{gain_sign}{h.gain_loss_percent:.1f}%"

            # Format period changes
            d1_sign = "+" if h.change_1d_pct >= 0 else ""
            d1_text = f"{d1_sign}{h.change_1d_pct:.2f}%"

            mtd_sign = "+" if h.change_mtd_pct >= 0 else ""
            mtd_text = f"{mtd_sign}{h.change_mtd_pct:.1f}%"

            ytd_sign = "+" if h.change_ytd_pct >= 0 else ""
            ytd_text = f"{ytd_sign}{h.change_ytd_pct:.1f}%"

            # Format shares: show decimals only if fractional
            if h.shares == int(h.shares):
                shares_text = f"{int(h.shares):,}"
            else:
                shares_text = f"{h.shares:,.4f}".rstrip("0").rstrip(".")

            table.add_row(
                h.symbol,
                shares_text,
                f"{currency}{h.total_cost:,.0f}",
                f"{currency}{h.total_value:,.0f}",
                Text(gain_text, style=gain_style),
                Text(d1_text, style=d1_style),
                Text(mtd_text, style=mtd_style),
                Text(ytd_text, style=ytd_style),
            )

        sections = [table]
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p")
            sections.append(Text(""))
            sections.append(Text(f"Last updated: {updated_time} | P to refresh", style="dim"))

        return Group(*sections)
