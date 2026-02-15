"""Service for market dashboard data and formatting."""

from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.fred_client import FREDClient
from boomberg.api.models import Quote


class DashboardService:
    """Service for market dashboard data and formatting."""

    # Index name mappings for display
    INDEX_NAMES = {
        # US
        "^GSPC": "S&P 500",
        "^DJI": "Dow Jones",
        "^IXIC": "NASDAQ",
        "^RUT": "Russell 2000",
        # Europe
        "^FTSE": "FTSE 100",
        "^GDAXI": "DAX",
        "^FCHI": "CAC 40",
        "^STOXX50E": "Euro STOXX",
        "^IBEX": "IBEX 35",
        "^AEX": "AEX",
        # Asia-Pacific
        "^N225": "Nikkei 225",
        "^HSI": "Hang Seng",
        "^KS11": "KOSPI",
        "^AXJO": "ASX 200",
        "^BSESN": "Sensex",
        "^TWII": "Taiwan",
        "^STI": "Singapore",
    }

    def __init__(self, fmp_client: FMPClient, fred_client: Optional[FREDClient] = None):
        self._fmp = fmp_client
        self._fred = fred_client

    async def get_world_indices(self) -> list[Quote]:
        """Get quotes for major world indices."""
        return await self._fmp.get_world_indices()

    async def get_most_active(self, limit: int = 20) -> list[Quote]:
        """Get most actively traded stocks by volume."""
        return await self._fmp.get_most_active(limit)

    async def get_treasury_rates(self) -> tuple[dict, dict | None]:
        """Get current US Treasury rates with previous day for comparison."""
        return await self._fmp.get_treasury_rates()

    async def get_forex_rates(self) -> list[Quote]:
        """Get currency ETF quotes as forex proxy."""
        return await self._fmp.get_forex_quotes()

    async def get_economic_stats(self) -> dict:
        """Get economic statistics from FRED.

        Returns:
            Dictionary of economic indicators, or empty dict if FRED not configured
        """
        if not self._fred:
            return {}
        return await self._fred.get_economic_indicators()

    def format_indices(self, quotes: list[Quote]) -> str:
        """Format world indices for display."""
        if not quotes:
            return "[dim]No index data available.[/dim]"

        # Separate by region
        us_symbols = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
        europe_symbols = ["^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^IBEX", "^AEX"]
        asia_symbols = ["^N225", "^HSI", "^KS11", "^AXJO", "^BSESN", "^TWII", "^STI"]

        us_indices = [q for q in quotes if q.symbol in us_symbols]
        europe_indices = [q for q in quotes if q.symbol in europe_symbols]
        asia_indices = [q for q in quotes if q.symbol in asia_symbols]

        lines = []
        lines.append("=" * 80)
        lines.append("                         WORLD EQUITY INDICES")
        lines.append("=" * 80)
        lines.append("")

        def format_index_colored(q: Quote) -> str:
            """Return index with colored change percentage."""
            name = self.INDEX_NAMES.get(q.symbol, q.symbol)
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            pct = f"{sign}{q.change_percent:.2f}%"
            return f"{name:<12} {q.price:>12,.2f}  [{change_color}]{pct:>8}[/{change_color}]"

        # Print US MARKETS header
        lines.append("US MARKETS")
        lines.append("-" * 38)
        for q in us_indices:
            lines.append(format_index_colored(q))

        lines.append("")

        # Print EUROPE header
        lines.append("EUROPE")
        lines.append("-" * 38)
        for q in europe_indices:
            lines.append(format_index_colored(q))

        lines.append("")

        # Print ASIA-PACIFIC header
        lines.append("ASIA-PACIFIC")
        lines.append("-" * 38)
        for q in asia_indices:
            lines.append(format_index_colored(q))

        return "\n".join(lines)

    def format_most_active(self, quotes: list[Quote]) -> str:
        """Format market movers (biggest gainers) for display."""
        if not quotes:
            return "[dim]No data available.[/dim]"

        lines = []
        lines.append("=" * 65)
        lines.append("                    MARKET MOVERS (GAINERS)")
        lines.append("=" * 65)
        lines.append("")
        lines.append(" #   Symbol      Price        Change")
        lines.append("-" * 3 + "  " + "-" * 10 + "  " + "-" * 10 + "  " + "-" * 12)

        for i, q in enumerate(quotes, 1):
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            lines.append(
                f"{i:>2}   {q.symbol:<10}  ${q.price:>9,.2f}  "
                f"[{change_color}]{sign}{q.change_percent:>8.2f}%[/{change_color}]"
            )

        return "\n".join(lines)

    def format_treasury_rates(self, rates: dict | tuple[dict, dict | None]) -> str:
        """Format treasury rates for display."""
        # Handle both old dict format and new tuple format
        if isinstance(rates, tuple):
            current, previous = rates
        else:
            current, previous = rates, None

        if not current:
            return "[dim]No treasury rate data available.[/dim]"

        lines = []
        lines.append("=" * 65)
        lines.append("                    US TREASURY YIELDS")
        lines.append("=" * 65)
        lines.append("")

        # Map maturity keys to display names
        maturities = [
            ("month1", "1M"),
            ("month3", "3M"),
            ("month6", "6M"),
            ("year1", "1Y"),
            ("year2", "2Y"),
            ("year5", "5Y"),
            ("year10", "10Y"),
            ("year30", "30Y"),
        ]

        # Build yield curve data
        yields = []
        labels = []
        for key, label in maturities:
            value = current.get(key)
            if value is not None:
                yields.append(value)
                labels.append(label)

        # Render simple ASCII yield curve
        if len(yields) >= 2:
            lines.append("[bold]Yield Curve[/bold]")
            lines.append("")

            min_yield = min(yields)
            max_yield = max(yields)
            chart_height = 8
            chart_width = len(yields)

            # Normalize yields to chart height
            if max_yield > min_yield:
                normalized = [(y - min_yield) / (max_yield - min_yield) * (chart_height - 1) for y in yields]
            else:
                normalized = [chart_height // 2] * len(yields)

            # Build chart rows (top to bottom)
            for row in range(chart_height - 1, -1, -1):
                if row == chart_height - 1:
                    label = f"{max_yield:.1f}%"
                elif row == 0:
                    label = f"{min_yield:.1f}%"
                else:
                    label = "     "

                line = f"{label:>6} |"
                for i, norm_val in enumerate(normalized):
                    if round(norm_val) == row:
                        line += "   *   "
                    elif round(norm_val) > row:
                        line += "   |   "
                    else:
                        line += "       "
                lines.append(line)

            # X-axis
            lines.append("       +" + "-------" * len(labels))
            axis_labels = "        "
            for label in labels:
                axis_labels += f"{label:^7}"
            lines.append(axis_labels)
            lines.append("")

        # Table header
        lines.append("Maturity        Yield      Change")
        lines.append("-" * 14 + "  " + "-" * 7 + "  " + "-" * 10)

        # Map for table display
        table_maturities = [
            ("month1", "1 Month"),
            ("month3", "3 Month"),
            ("month6", "6 Month"),
            ("year1", "1 Year"),
            ("year2", "2 Year"),
            ("year5", "5 Year"),
            ("year10", "10 Year"),
            ("year30", "30 Year"),
        ]

        for key, name in table_maturities:
            value = current.get(key)
            if value is not None:
                # Calculate change if previous data available
                if previous and previous.get(key) is not None:
                    prev_value = previous.get(key)
                    change_bp = (value - prev_value) * 100
                    change_color = "green" if change_bp >= 0 else "red"
                    sign = "+" if change_bp >= 0 else ""
                    bp_str = f"{sign}{change_bp:.1f}bp"
                    change_str = f"[{change_color}]{bp_str:>10}[/{change_color}]"
                else:
                    change_str = "[dim]       N/A[/dim]"
                lines.append(f"{name:<14}  {value:>6.2f}%  {change_str}")
            else:
                lines.append(f"{name:<14}  [dim]   N/A[/dim]  [dim]       N/A[/dim]")

        return "\n".join(lines)

    # Currency ETF name mappings
    CURRENCY_ETF_NAMES = {
        "FXE": "Euro (EUR)",
        "FXY": "Yen (JPY)",
        "FXB": "Pound (GBP)",
        "FXC": "CAD",
        "FXA": "AUD",
        "UUP": "USD Index",
    }

    def format_forex(self, quotes: list[Quote]) -> str:
        """Format currency ETF quotes for display."""
        if not quotes:
            return "[dim]No currency data available.[/dim]"

        lines = []
        lines.append("=" * 60)
        lines.append("                      CURRENCY ETFs")
        lines.append("=" * 60)
        lines.append("")
        lines.append("Symbol      Currency        Price      Change")
        lines.append("-" * 10 + "  " + "-" * 12 + "  " + "-" * 9 + "  " + "-" * 10)

        for q in quotes:
            currency_name = self.CURRENCY_ETF_NAMES.get(q.symbol, q.name[:12])
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            pct = f"{sign}{q.change_percent:.2f}%"

            lines.append(
                f"{q.symbol:<10}  {currency_name:<12}  ${q.price:>8.2f}  "
                f"[{change_color}]{pct:>10}[/{change_color}]"
            )

        return "\n".join(lines)

    def format_economic_stats(self, stats: dict) -> str:
        """Format economic statistics for display."""
        if not stats:
            return "[dim]No economic data available. Set FRED_API_KEY to enable this feature.[/dim]"

        lines = []
        lines.append("=" * 65)
        lines.append("                    ECONOMIC STATISTICS")
        lines.append("=" * 65)
        lines.append("")
        lines.append("INDICATOR                VALUE         DATE")
        lines.append("-" * 21 + "    " + "-" * 12 + "  " + "-" * 10)

        # Format each indicator
        indicator_formats = {
            "GDP": ("GDP (Quarterly)", self._format_gdp),
            "Unemployment": ("Unemployment Rate", self._format_percent),
            "CPI": ("CPI (Inflation)", self._format_cpi),
            "Fed Funds Rate": ("Fed Funds Rate", self._format_percent),
            "10Y Treasury": ("10Y Treasury Yield", self._format_percent),
        }

        for key, (name, formatter) in indicator_formats.items():
            obs = stats.get(key)
            if obs:
                value = obs.get("value", ".")
                date = obs.get("date", "")
                if value != ".":
                    formatted_value = formatter(value)
                    lines.append(f"{name:<21}    {formatted_value:<12}  {date}")
                else:
                    lines.append(f"{name:<21}    [dim]N/A[/dim]")
            else:
                lines.append(f"{name:<21}    [dim]N/A[/dim]")

        return "\n".join(lines)

    def format_news(self, articles: list) -> str:
        """Format top news headlines for display."""
        if not articles:
            return "[dim]No news available.[/dim]"

        lines = []
        lines.append("=" * 65)
        lines.append("                    TOP NEWS HEADLINES")
        lines.append("=" * 65)
        lines.append("")

        for i, article in enumerate(articles[:15], 1):
            title = article.title[:60] + "..." if len(article.title) > 60 else article.title
            source = article.site if hasattr(article, "site") else ""
            lines.append(f"[bold white]{i:>2}. {title}[/bold white]")
            if source:
                lines.append(f"    [dim]{source}[/dim]")
            lines.append("")

        return "\n".join(lines)

    def _format_volume(self, volume: int) -> str:
        """Format volume with suffix (K, M, B)."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.1f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.1f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.1f}K"
        return str(volume)

    def _format_gdp(self, value: str) -> str:
        """Format GDP value."""
        try:
            val = float(value)
            return f"${val / 1000:.2f}T"
        except (ValueError, TypeError):
            return value

    def _format_percent(self, value: str) -> str:
        """Format percentage value."""
        try:
            return f"{float(value):.2f}%"
        except (ValueError, TypeError):
            return value

    def _format_cpi(self, value: str) -> str:
        """Format CPI value."""
        try:
            return f"{float(value):.1f}"
        except (ValueError, TypeError):
            return value
