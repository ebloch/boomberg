"""Quote display panel widget."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from boomberg.api.models import NewsArticle, Quote


@dataclass
class PriceChanges:
    """Price changes over various time periods."""
    change_3m: float = 0.0
    change_ytd: float = 0.0
    change_5y: float = 0.0
    change_10y: float = 0.0

# Exchange to currency symbol mapping
EXCHANGE_CURRENCY = {
    # US Exchanges
    "NYSE": "$",
    "NASDAQ": "$",
    "AMEX": "$",
    "NYSEArca": "$",
    "BATS": "$",
    "OTC": "$",
    # Japan
    "JPX": "¥",
    "TSE": "¥",
    "Tokyo": "¥",
    # UK
    "LSE": "£",
    "London": "£",
    # Europe (EUR)
    "XETRA": "€",
    "Frankfurt": "€",
    "Euronext": "€",
    "Paris": "€",
    "Amsterdam": "€",
    "Brussels": "€",
    "Milan": "€",
    # Switzerland
    "SIX": "CHF ",
    "Swiss": "CHF ",
    # Hong Kong
    "HKEX": "HK$",
    "HKSE": "HK$",
    "HKG": "HK$",
    "Hong Kong": "HK$",
    # China
    "Shanghai": "¥",
    "Shenzhen": "¥",
    "SSE": "¥",
    "SZSE": "¥",
    # Korea
    "KRX": "₩",
    "KSC": "₩",
    "KOSPI": "₩",
    "Korea": "₩",
    # India
    "NSE": "₹",
    "BSE": "₹",
    # Australia
    "ASX": "A$",
    # Canada
    "TSX": "C$",
    "Toronto": "C$",
    # Singapore
    "SGX": "S$",
    # Taiwan
    "TWSE": "NT$",
    "Taiwan": "NT$",
    # Brazil
    "BOVESPA": "R$",
    "B3": "R$",
}


def get_currency_symbol(exchange: str) -> str:
    """Get currency symbol for an exchange."""
    if not exchange:
        return "$"
    # Check direct match
    if exchange in EXCHANGE_CURRENCY:
        return EXCHANGE_CURRENCY[exchange]
    # Check partial matches (exchange names can vary)
    exchange_lower = exchange.lower()
    for key, symbol in EXCHANGE_CURRENCY.items():
        if key.lower() in exchange_lower or exchange_lower in key.lower():
            return symbol
    # Default to USD
    return "$"


class QuotePanel(Static):
    """Widget for displaying a stock quote."""

    DEFAULT_CSS = """
    QuotePanel {
        width: 100%;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }

    QuotePanel.up {
        border: solid $success;
    }

    QuotePanel.down {
        border: solid $error;
    }
    """

    def __init__(self, quote: Optional[Quote] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._quote = quote
        self._price_changes: Optional[PriceChanges] = None
        self._news: list[NewsArticle] = []

    def update_quote(
        self,
        quote: Quote,
        price_changes: Optional[PriceChanges] = None,
        news: Optional[list[NewsArticle]] = None,
    ) -> None:
        """Update the displayed quote."""
        self._quote = quote
        self._price_changes = price_changes
        self._news = news[:3] if news else []
        self.remove_class("up", "down")
        if quote.change > 0:
            self.add_class("up")
        elif quote.change < 0:
            self.add_class("down")
        self.refresh()

    def render(self) -> RenderableType:
        """Render the quote panel."""
        if self._quote is None:
            return Text("No quote loaded. Use Q <SYMBOL> to load a quote.", style="dim")

        q = self._quote
        change_style = "green" if q.change >= 0 else "red"
        sign = "+" if q.change >= 0 else ""
        currency = get_currency_symbol(q.exchange)

        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("Label", style="bold cyan")
        table.add_column("Value", style="white")

        # Header with symbol and name
        header = Text()
        header.append(f"{q.symbol}", style="bold yellow")
        if q.name:
            header.append(f"  {q.name}", style="dim")

        # Price and change
        price_text = Text()
        price_text.append(f"{currency}{q.price:,.2f}", style="bold white")
        price_text.append(f"  {sign}{q.change:,.2f} ({sign}{q.change_percent:.2f}%)", style=change_style)

        table.add_row("", header)
        table.add_row("Price", price_text)
        table.add_row("Day Range", f"{currency}{q.day_low:,.2f} - {currency}{q.day_high:,.2f}")
        table.add_row("52W Range", f"{currency}{q.year_low:,.2f} - {currency}{q.year_high:,.2f}")
        table.add_row("Volume", self._format_volume(q.volume))
        table.add_row("Avg Volume", self._format_volume(q.avg_volume))

        if q.market_cap:
            table.add_row("Market Cap", self._format_market_cap(q.market_cap, currency))
        if q.pe:
            table.add_row("P/E Ratio", f"{q.pe:.2f}")
        if q.eps:
            table.add_row("EPS", f"{currency}{q.eps:.2f}")

        # Price changes over time
        if self._price_changes:
            pc = self._price_changes
            changes_text = Text()
            changes_text.append(self._format_change("3M", pc.change_3m))
            changes_text.append("  ")
            changes_text.append(self._format_change("YTD", pc.change_ytd))
            changes_text.append("  ")
            changes_text.append(self._format_change("5Y", pc.change_5y))
            changes_text.append("  ")
            changes_text.append(self._format_change("10Y", pc.change_10y))
            table.add_row("Performance", changes_text)

        if q.exchange:
            table.add_row("Exchange", q.exchange)

        # Add news section if we have news
        if self._news:
            renderables = [table, Text(""), self._render_news()]
            return Group(*renderables)

        return table

    def _format_change(self, label: str, value: float) -> Text:
        """Format a labeled percentage change."""
        style = "green" if value >= 0 else "red"
        sign = "+" if value >= 0 else ""
        text = Text()
        text.append(f"{label}: ", style="dim")
        text.append(f"{sign}{value:.1f}%", style=style)
        return text

    def _format_market_cap(self, market_cap: float, currency: str = "$") -> str:
        """Format market cap in human-readable form."""
        if market_cap >= 1e12:
            return f"{currency}{market_cap / 1e12:.2f}T"
        if market_cap >= 1e9:
            return f"{currency}{market_cap / 1e9:.2f}B"
        if market_cap >= 1e6:
            return f"{currency}{market_cap / 1e6:.2f}M"
        return f"{currency}{market_cap:,.0f}"

    def _format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1e9:
            return f"{volume / 1e9:.2f}B"
        if volume >= 1e6:
            return f"{volume / 1e6:.2f}M"
        if volume >= 1e3:
            return f"{volume / 1e3:.2f}K"
        return f"{volume:,}"

    def _render_news(self) -> Table:
        """Render news headlines section."""
        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("Content", style="white")

        table.add_row(Text("News", style="bold cyan"))

        for article in self._news:
            # Title
            table.add_row(Text(article.title, style="white"))

            # Source (clickable) and time
            time_str = self._format_relative_time(article.published_date)
            if article.url:
                source_text = Text(article.site, style="dim")
                source_text.stylize(f"link {article.url}")
                meta_text = Text()
                meta_text.append_text(source_text)
                meta_text.append(f" - {time_str}", style="dim")
                table.add_row(meta_text)
            else:
                table.add_row(Text(f"{article.site} - {time_str}", style="dim"))
            table.add_row(Text(""))  # Spacing between articles

        return table

    def _format_relative_time(self, published_date: datetime) -> str:
        """Format published date as relative time."""
        if published_date.tzinfo is None:
            now = datetime.utcnow()
        else:
            now = datetime.now(published_date.tzinfo)
        diff = now - published_date

        if diff.total_seconds() < 0:
            return "Just now"

        if diff.days == 0:
            hours = diff.seconds // 3600
            if hours == 0:
                minutes = diff.seconds // 60
                return f"{minutes}m ago" if minutes > 0 else "Just now"
            return f"{hours}h ago"
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return published_date.strftime("%b %d")
