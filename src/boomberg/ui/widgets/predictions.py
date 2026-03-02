"""Predictions widget for displaying Kalshi prediction markets."""

from datetime import datetime
from typing import Optional

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from boomberg.api.kalshi_models import KalshiMarket
from boomberg.services.predictions import SERIES_CATEGORIES, CATEGORY_ORDER


class PredictionWidget(Static):
    """Widget for displaying prediction market data."""

    DEFAULT_CSS = """
    PredictionWidget {
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
        self._markets: Optional[list[KalshiMarket]] = None
        self._detail: Optional[KalshiMarket] = None
        self._last_updated: Optional[datetime] = None

    def update_markets(self, markets: list[KalshiMarket]) -> None:
        """Update with list of markets for overview display."""
        self._markets = markets
        self._detail = None
        self._last_updated = datetime.now()
        self.refresh()

    def update_detail(self, market: KalshiMarket) -> None:
        """Update with single market for detail display."""
        self._detail = market
        self._markets = None
        self._last_updated = datetime.now()
        self.refresh()

    def render(self) -> RenderableType:
        """Render the predictions widget."""
        if self._detail:
            return self._render_detail()
        elif self._markets:
            return self._render_markets()
        else:
            return Text("Loading prediction markets...", style="dim italic")

    def _format_price_cents(self, cents: Optional[int]) -> str:
        """Format price in cents."""
        if cents is None:
            return "-"
        return f"{cents}c"

    def _format_change(self, market: KalshiMarket) -> Text:
        """Format price change with styling."""
        change = market.change_cents
        if change > 0:
            return Text(f"+{change}c", style="green")
        elif change < 0:
            return Text(f"{change}c", style="red")
        return Text("0c", style="dim")

    def _format_volume(self, volume: int) -> str:
        """Format volume in human-readable form."""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        if volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        return str(volume)

    def _truncate_title(self, title: str, max_length: int = 50) -> str:
        """Truncate title to max length with ellipsis."""
        if len(title) <= max_length:
            return title
        return title[: max_length - 3] + "..."

    def _shorten_title(self, title: str, series_ticker: Optional[str]) -> str:
        """Shorten title by removing redundant prefixes based on series.

        Args:
            title: The full market title
            series_ticker: The series ticker (e.g., KXFED, KXCPI)

        Returns:
            A shortened title with common prefixes removed
        """
        import re

        if not series_ticker:
            return title

        result = title

        # Remove common "Will the..." prefixes for Fed markets
        if series_ticker in ("KXFED", "KXFEDDECISION", "KXRATECUT", "KXRATECUTCOUNT"):
            # Remove "Will the Federal Reserve" prefix
            result = re.sub(r"^Will the Federal Reserve\s+", "", result)
            result = re.sub(r"^Will the Fed\s+", "", result)
            # Convert "at their March 2026 meeting" -> "in March 2026" to preserve date for extraction
            result = re.sub(
                r"\s+at their\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+meeting",
                r" in \1 \2",
                result,
                flags=re.IGNORECASE,
            )
            # Remove any remaining "at their meeting" without date
            result = re.sub(r"\s+at their\s+meeting", "", result)
            result = re.sub(r"rates by ", "", result)

        # Remove common prefixes for CPI markets
        elif series_ticker in ("KXCPI", "KXCPICORE", "KXCPIYOY"):
            result = re.sub(r"^Will the rate of CPI inflation be\s+", "", result)
            result = re.sub(r"^Will the rate of core CPI inflation be\s+", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^Will CPI\s+", "", result)
            result = re.sub(r"^Will core CPI\s+", "", result, flags=re.IGNORECASE)
            # Remove filler phrase "for the year ending"
            result = re.sub(r"\s+for the year ending", "", result)

        # Remove common prefixes for employment markets
        elif series_ticker in ("KXU3", "KXPAYROLLS"):
            result = re.sub(r"^Will the unemployment rate \(U-3\) be\s+", "U-3 ", result)
            result = re.sub(r"^Will (the )?unemployment\s+", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^Will (the )?U\.?S\.?\s+(economy\s+)?", "", result, flags=re.IGNORECASE)
            # Clean up remaining "Rate (U-3) be" patterns
            result = re.sub(r"^Rate \(U-3\) be\s+", "U-3 ", result)

        # Remove common prefixes for GDP markets
        elif series_ticker == "KXGDP":
            result = re.sub(r"^Will (the )?U\.?S\.?\s+GDP\s+", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^Will (the )?GDP\s+", "", result, flags=re.IGNORECASE)

        # Remove common prefixes for recession markets
        elif series_ticker == "KXRECSSNBER":
            result = re.sub(r"^Will (the )?U\.?S\.?\s+(enter\s+a\s+)?", "", result, flags=re.IGNORECASE)
            result = re.sub(r"^Will (there be\s+a\s+)?", "", result, flags=re.IGNORECASE)

        # Extract date context and format nicely
        # Look for month names and years
        date_match = re.search(
            r"(in|by|before|after)?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4})?",
            result,
            re.IGNORECASE,
        )

        if date_match:
            month = date_match.group(2)
            year = date_match.group(3)
            # Abbreviate month
            month_abbrev = month[:3]
            # Remove the original date from the string and add abbreviated version
            result = re.sub(
                r"\s*(in|by|before|after)?\s*(January|February|March|April|May|June|July|August|September|October|November|December)\s*(\d{4})?\??",
                "",
                result,
                flags=re.IGNORECASE,
            )
            result = result.strip().rstrip("?")
            if year:
                result = f"{result} ({month_abbrev} {year})"
            else:
                result = f"{result} ({month_abbrev})"

        # Capitalize first letter
        if result and result[0].islower():
            result = result[0].upper() + result[1:]

        return result.strip()

    def _group_markets_by_category(
        self, markets: list[KalshiMarket]
    ) -> dict[str, list[KalshiMarket]]:
        """Group markets by their category."""
        grouped: dict[str, list[KalshiMarket]] = {}
        for market in markets:
            if market.series_ticker and market.series_ticker in SERIES_CATEGORIES:
                category = SERIES_CATEGORIES[market.series_ticker]
            else:
                category = "Other"
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(market)

        # Sort each category's markets by volume
        for category in grouped:
            grouped[category].sort(key=lambda m: m.volume_24h, reverse=True)

        # Return in category order
        ordered: dict[str, list[KalshiMarket]] = {}
        for category in CATEGORY_ORDER:
            if category in grouped:
                ordered[category] = grouped[category]
        # Add any "Other" category at the end
        if "Other" in grouped:
            ordered["Other"] = grouped["Other"]

        return ordered

    def _render_markets(self) -> RenderableType:
        """Render markets overview table grouped by category."""
        self.border_title = "Prediction Markets (Kalshi)"

        if not self._markets:
            return Text("No markets available.", style="dim italic")

        grouped = self._group_markets_by_category(self._markets)
        sections = []

        first_category = True
        for category, markets in grouped.items():
            # Add spacing between categories (except first)
            if not first_category:
                sections.append(Text(""))
            first_category = False

            # Table for this category - category name IS the first column header
            table = Table(
                box=None,
                padding=(0, 2),
                expand=True,
                show_header=True,
                header_style="bold cyan",
            )

            table.add_column(category, ratio=1, no_wrap=True)
            table.add_column("Yes", justify="right", width=6)
            table.add_column("No", justify="right", width=6)
            table.add_column("1D", justify="right", width=6)
            table.add_column("Vol 24h", justify="right", width=10)

            for market in markets:
                # Use shortened title, then truncate if still too long
                title = self._shorten_title(market.title, market.series_ticker)
                title = self._truncate_title(title)
                yes_price = self._format_price_cents(market.yes_bid)
                no_price = self._format_price_cents(market.no_bid)
                change = self._format_change(market)
                volume = self._format_volume(market.volume_24h)

                table.add_row(title, yes_price, no_price, change, volume)

            sections.append(table)

        sections.append(Text(""))

        footer_parts = []
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p")
            footer_parts.append(f"Last updated: {updated_time}")
        footer_parts.append("PRED to refresh")
        footer_parts.append("PRED <TICKER> for detail")

        sections.append(Text(" | ".join(footer_parts), style="dim"))

        return Group(*sections)

    def _render_detail(self) -> RenderableType:
        """Render single market detail view."""
        if not self._detail:
            return Text("No market data available.", style="dim italic")

        market = self._detail
        self.border_title = f"Prediction Market: {market.ticker}"

        sections = []

        # Market title
        sections.append(Text("=" * 70, style="cyan"))
        sections.append(Text(f"  {market.title}", style="bold"))
        sections.append(Text("=" * 70, style="cyan"))
        sections.append(Text(""))

        # Current prices section
        sections.append(Text("Current Prices", style="bold yellow"))

        price_table = Table(box=None, padding=(0, 2), show_header=False)
        price_table.add_column("Label", width=20)
        price_table.add_column("Value", width=20)

        yes_bid = self._format_price_cents(market.yes_bid)
        yes_ask = self._format_price_cents(market.yes_ask)
        no_bid = self._format_price_cents(market.no_bid)
        no_ask = self._format_price_cents(market.no_ask)
        last_price = self._format_price_cents(market.last_price)

        price_table.add_row("  YES Bid/Ask:", f"{yes_bid} / {yes_ask}")
        price_table.add_row("  NO  Bid/Ask:", f"{no_bid} / {no_ask}")
        price_table.add_row("  Last Price:", last_price)

        sections.append(price_table)
        sections.append(Text(""))

        # Change section
        change = self._format_change(market)
        prev_price = self._format_price_cents(market.previous_price)
        change_line = Text("Change: ")
        change_line.append_text(change)
        change_line.append(f" (from {prev_price})")
        sections.append(change_line)
        sections.append(Text(""))

        # Activity section
        sections.append(Text("Activity", style="bold yellow"))

        activity_table = Table(box=None, padding=(0, 2), show_header=False)
        activity_table.add_column("Label", width=20)
        activity_table.add_column("Value", width=20)

        volume = self._format_volume(market.volume_24h)
        open_interest = self._format_volume(market.open_interest) if market.open_interest else "-"
        status = market.status.capitalize()
        close_time = market.close_time or "-"

        activity_table.add_row("  24h Volume:", volume)
        activity_table.add_row("  Open Interest:", open_interest)
        activity_table.add_row("  Status:", status)
        activity_table.add_row("  Closes:", close_time)

        sections.append(activity_table)
        sections.append(Text(""))

        # Footer
        footer_parts = []
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p")
            footer_parts.append(f"Last updated: {updated_time}")
        footer_parts.append(f"PRED {market.ticker} to refresh")
        footer_parts.append("PRED for overview")

        sections.append(Text(" | ".join(footer_parts), style="dim"))

        return Group(*sections)
