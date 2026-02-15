"""Watchlist widget for displaying multiple quotes."""

from dataclasses import dataclass

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.message import Message
from textual.widgets import Static

from boomberg.api.models import Quote
from boomberg.ui.widgets.quote_panel import get_currency_symbol


class WatchlistWidget(Static):
    """Widget for displaying a watchlist of quotes."""

    DEFAULT_CSS = """
    WatchlistWidget {
        width: 100%;
        height: auto;
        min-height: 10;
        padding: 1;
        background: $surface;
        border: solid $primary;
    }

    WatchlistWidget .watchlist-header {
        text-style: bold;
        color: $secondary;
    }
    """

    @dataclass
    class SymbolSelected(Message):
        """Message sent when a symbol is selected."""

        symbol: str

    def __init__(self, name: str = "Watchlist", **kwargs) -> None:
        super().__init__(**kwargs)
        self._name = name
        self._quotes: list[Quote] = []
        self._empty_message = "Watchlist is empty. Use 'WA <SYMBOL>' to add symbols."

    def update_quotes(self, quotes: list[Quote]) -> None:
        """Update the displayed quotes."""
        self._quotes = quotes
        self.refresh()

    def set_empty_message(self, message: str) -> None:
        """Set the message shown when watchlist is empty."""
        self._empty_message = message

    def render(self) -> RenderableType:
        """Render the watchlist."""
        if not self._quotes:
            return Text(self._empty_message, style="dim italic")

        table = Table(
            title=self._name,
            title_style="bold cyan",
            box=None,
            padding=(0, 1),
            expand=True,
        )
        table.add_column("Symbol", style="bold yellow", width=8)
        table.add_column("Price", justify="right", width=12)
        table.add_column("Change", justify="right", width=10)
        table.add_column("% Chg", justify="right", width=8)
        table.add_column("Volume", justify="right", width=10)

        for quote in self._quotes:
            change_style = "green" if quote.change >= 0 else "red"
            sign = "+" if quote.change >= 0 else ""
            currency = get_currency_symbol(quote.exchange)

            table.add_row(
                quote.symbol,
                f"{currency}{quote.price:,.2f}",
                Text(f"{sign}{quote.change:,.2f}", style=change_style),
                Text(f"{sign}{quote.change_percent:.2f}%", style=change_style),
                self._format_volume(quote.volume),
            )

        return table

    def _format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1e9:
            return f"{volume / 1e9:.1f}B"
        if volume >= 1e6:
            return f"{volume / 1e6:.1f}M"
        if volume >= 1e3:
            return f"{volume / 1e3:.1f}K"
        return f"{volume:,}"
