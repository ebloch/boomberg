"""Watchlist widget for displaying multiple quotes."""

from dataclasses import dataclass
from typing import Union

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text
from textual.message import Message
from textual.widgets import Static

from boomberg.api.models import Quote
from boomberg.services.watchlist import WatchlistQuote
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
        self._quotes: list[Union[Quote, WatchlistQuote]] = []
        self._empty_message = "Watchlist is empty. Use 'WA <SYMBOL>' to add symbols."

    def update_quotes(self, quotes: list[Union[Quote, WatchlistQuote]]) -> None:
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
            row_styles=["on grey23", ""],
        )
        table.add_column("Symbol", style="bold yellow", width=8)
        table.add_column("Mkt Cap", justify="right", width=10)
        table.add_column("PE", justify="right", width=7)
        table.add_column("1D", justify="right", width=8)
        table.add_column("1M", justify="right", width=8)
        table.add_column("YTD", justify="right", width=8)
        table.add_column("3Y", justify="right", width=8)
        table.add_column("Volume", justify="right", width=10)

        for quote in self._quotes:
            # Get price change values (handle both Quote and WatchlistQuote)
            if isinstance(quote, WatchlistQuote):
                change_1d = quote.change_1d
                change_1m = quote.change_1m
                change_ytd = quote.change_ytd
                change_3y = quote.change_3y
                market_cap = quote.market_cap
                pe = quote.pe
            else:
                change_1d = quote.change_percent
                change_1m = 0.0
                change_ytd = 0.0
                change_3y = 0.0
                market_cap = quote.market_cap
                pe = quote.pe

            table.add_row(
                quote.symbol,
                self._format_market_cap(market_cap),
                self._format_pe(pe),
                self._format_change(change_1d),
                self._format_change(change_1m),
                self._format_change(change_ytd),
                self._format_change(change_3y),
                self._format_volume(quote.volume),
            )

        return table

    def _format_change(self, value: float) -> Text:
        """Format a percentage change with color."""
        style = "green" if value >= 0 else "red"
        sign = "+" if value >= 0 else ""
        return Text(f"{sign}{value:.1f}%", style=style)

    def _format_market_cap(self, market_cap: float | None) -> str:
        """Format market cap in human-readable form."""
        if market_cap is None:
            return "-"
        if market_cap >= 1e12:
            return f"${market_cap / 1e12:.1f}T"
        if market_cap >= 1e9:
            return f"${market_cap / 1e9:.1f}B"
        if market_cap >= 1e6:
            return f"${market_cap / 1e6:.1f}M"
        return f"${market_cap:,.0f}"

    def _format_pe(self, pe: float | None) -> str:
        """Format PE ratio."""
        if pe is None:
            return "-"
        return f"{pe:.1f}"

    def _format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1e9:
            return f"{volume / 1e9:.1f}B"
        if volume >= 1e6:
            return f"{volume / 1e6:.1f}M"
        if volume >= 1e3:
            return f"{volume / 1e3:.1f}K"
        return f"{volume:,}"
