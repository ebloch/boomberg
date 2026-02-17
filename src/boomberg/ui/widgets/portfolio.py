"""Portfolio widget for displaying holdings and performance."""

from rich.console import RenderableType
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
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._holdings: list[PortfolioHolding] = []
        self._empty_message = "Portfolio is empty. Use 'PA <SYMBOL> <SHARES> <COST>' to add holdings."

    def update_holdings(self, holdings: list[PortfolioHolding]) -> None:
        """Update the displayed holdings."""
        self._holdings = holdings
        self.refresh()

    def set_empty_message(self, message: str) -> None:
        """Set the message shown when portfolio is empty."""
        self._empty_message = message

    def render(self) -> RenderableType:
        """Render the portfolio."""
        if not self._holdings:
            return Text(self._empty_message, style="dim italic")

        table = Table(
            title="Portfolio",
            title_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=True,
        )

        # Columns
        table.add_column("Symbol", style="bold yellow", width=8)
        table.add_column("Shares", justify="right", width=8)
        table.add_column("Price", justify="right", width=10)
        table.add_column("Value", justify="right", width=12)
        table.add_column("Gain/Loss", justify="right", width=12)
        table.add_column("1D", justify="right", width=10)
        table.add_column("MTD", justify="right", width=10)
        table.add_column("YTD", justify="right", width=10)

        total_value = 0.0
        total_cost = 0.0
        total_1d_change = 0.0
        total_mtd_change = 0.0
        total_ytd_change = 0.0

        for h in self._holdings:
            currency = get_currency_symbol(h.exchange)
            gain_style = "green" if h.gain_loss >= 0 else "red"
            d1_style = "green" if h.change_1d_pct >= 0 else "red"
            mtd_style = "green" if h.change_mtd_pct >= 0 else "red"
            ytd_style = "green" if h.change_ytd_pct >= 0 else "red"

            # Format gain/loss
            gain_sign = "+" if h.gain_loss >= 0 else ""
            gain_text = f"{gain_sign}{currency}{abs(h.gain_loss):,.0f} ({gain_sign}{h.gain_loss_percent:.1f}%)"

            # Format period changes
            d1_sign = "+" if h.change_1d_pct >= 0 else ""
            d1_text = f"{d1_sign}{h.change_1d_pct:.2f}%"

            mtd_sign = "+" if h.change_mtd_pct >= 0 else ""
            mtd_text = f"{mtd_sign}{h.change_mtd_pct:.1f}%"

            ytd_sign = "+" if h.change_ytd_pct >= 0 else ""
            ytd_text = f"{ytd_sign}{h.change_ytd_pct:.1f}%"

            table.add_row(
                h.symbol,
                f"{h.shares:,.0f}",
                f"{currency}{h.current_price:,.2f}",
                f"{currency}{h.total_value:,.0f}",
                Text(gain_text, style=gain_style),
                Text(d1_text, style=d1_style),
                Text(mtd_text, style=mtd_style),
                Text(ytd_text, style=ytd_style),
            )

            total_value += h.total_value
            total_cost += h.total_cost
            total_1d_change += h.change_1d_value
            total_mtd_change += h.change_mtd_value
            total_ytd_change += h.change_ytd_value

        # Add totals row
        if self._holdings:
            total_gain = total_value - total_cost
            total_gain_pct = (total_gain / total_cost * 100) if total_cost > 0 else 0
            total_1d_pct = (total_1d_change / (total_value - total_1d_change) * 100) if (total_value - total_1d_change) > 0 else 0
            total_mtd_pct = (total_mtd_change / (total_value - total_mtd_change) * 100) if (total_value - total_mtd_change) > 0 else 0
            total_ytd_pct = (total_ytd_change / (total_value - total_ytd_change) * 100) if (total_value - total_ytd_change) > 0 else 0

            gain_style = "green" if total_gain >= 0 else "red"
            d1_style = "green" if total_1d_change >= 0 else "red"
            mtd_style = "green" if total_mtd_change >= 0 else "red"
            ytd_style = "green" if total_ytd_change >= 0 else "red"

            gain_sign = "+" if total_gain >= 0 else ""
            d1_sign = "+" if total_1d_change >= 0 else ""
            mtd_sign = "+" if total_mtd_change >= 0 else ""
            ytd_sign = "+" if total_ytd_change >= 0 else ""

            table.add_row("", "", "", "", "", "", "", "")  # Separator
            table.add_row(
                Text("TOTAL", style="bold white"),
                "",
                "",
                Text(f"${total_value:,.0f}", style="bold white"),
                Text(f"{gain_sign}${abs(total_gain):,.0f} ({gain_sign}{total_gain_pct:.1f}%)", style=f"bold {gain_style}"),
                Text(f"{d1_sign}{total_1d_pct:.2f}%", style=f"bold {d1_style}"),
                Text(f"{mtd_sign}{total_mtd_pct:.1f}%", style=f"bold {mtd_style}"),
                Text(f"{ytd_sign}{total_ytd_pct:.1f}%", style=f"bold {ytd_style}"),
            )

        return table
