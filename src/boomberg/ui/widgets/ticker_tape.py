"""Scrolling ticker tape widget."""

from rich.console import RenderableType
from rich.text import Text
from textual.widgets import Static

from boomberg.api.models import Quote


class TickerTape(Static):
    """Scrolling ticker tape showing quotes."""

    DEFAULT_CSS = """
    TickerTape {
        width: 100%;
        height: 1;
        dock: top;
        background: $primary-darken-2;
        color: $text;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._quotes: list[Quote] = []
        self._offset: int = 0

    def update_quotes(self, quotes: list[Quote]) -> None:
        """Update the quotes displayed in the ticker."""
        self._quotes = quotes
        self.refresh()

    def render(self) -> RenderableType:
        """Render the ticker tape."""
        if not self._quotes:
            return Text("No market data", style="dim")

        tape = Text()
        for i, quote in enumerate(self._quotes):
            if i > 0:
                tape.append("  |  ", style="dim")

            tape.append(quote.symbol, style="bold yellow")
            tape.append(f" ${quote.price:,.2f} ", style="white")

            change_style = "green" if quote.change >= 0 else "red"
            sign = "+" if quote.change >= 0 else ""
            tape.append(f"{sign}{quote.change_percent:.2f}%", style=change_style)

        return tape

    def scroll_tick(self) -> None:
        """Advance the scroll position (for animation)."""
        self._offset += 1
        self.refresh()
