"""Service for market dashboard data and formatting."""

import asyncio
from datetime import datetime
from typing import Optional, Union

from rich.console import RenderableType
from rich.table import Table
from rich.text import Text

from boomberg.api.client import FMPClient
from boomberg.api.eodhd_client import EODHDClient, COUNTRY_BONDS
from boomberg.api.fred_client import FREDClient
from boomberg.api.models import Quote


# Commodity ETF symbols and display names
COMMODITY_ETFS = ["GLD", "USO", "SLV", "UNG", "DBA", "URA"]
COMMODITY_NAMES = {
    "GLD": "Gold",
    "USO": "Oil",
    "SLV": "Silver",
    "UNG": "Nat Gas",
    "DBA": "Agri",
    "URA": "Uranium",
}

# Sector ETF symbols and display names
SECTOR_ETFS = ["XLK", "XLF", "XLE", "XLV", "XLY", "XLI"]
SECTOR_NAMES = {
    "XLK": "Tech",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLY": "Consumer",
    "XLI": "Industrials",
}

# Country display names (including US which uses FMP)
COUNTRY_NAMES = {
    "US": "United States",
    "CA": "Canada",
    "DE": "Germany",
    "UK": "United Kingdom",
    "JP": "Japan",
    "FR": "France",
    "AU": "Australia",
    "IT": "Italy",
    "ES": "Spain",
    "CN": "China",
}


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

    def __init__(
        self,
        fmp_client: FMPClient,
        fred_client: Optional[FREDClient] = None,
        eodhd_client: Optional[EODHDClient] = None,
    ):
        self._fmp = fmp_client
        self._fred = fred_client
        self._eodhd = eodhd_client

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

    async def get_commodity_quotes(self) -> list[Quote]:
        """Get quotes for commodity ETFs."""
        return await self._fmp.get_quotes(COMMODITY_ETFS)

    async def get_sector_quotes(self) -> list[Quote]:
        """Get quotes for sector ETFs."""
        return await self._fmp.get_quotes(SECTOR_ETFS)

    async def get_market_snapshot(self) -> dict:
        """Get complete market snapshot data in parallel.

        Returns:
            Dictionary with keys: indices, commodities, sectors, bonds
        """
        indices, commodities, sectors, rates = await asyncio.gather(
            self.get_world_indices(),
            self.get_commodity_quotes(),
            self.get_sector_quotes(),
            self.get_treasury_rates(),
        )

        # Handle treasury rates tuple
        bonds = rates[0] if isinstance(rates, tuple) else rates

        return {
            "indices": indices,
            "commodities": commodities,
            "sectors": sectors,
            "bonds": bonds or {},
        }

    def format_market_snapshot(self, snapshot: dict) -> str:
        """Format complete market snapshot for display."""
        if not snapshot:
            return "[dim]No snapshot data available.[/dim]"

        lines = []
        today = datetime.now().strftime("%b %d, %Y")

        # Header
        lines.append("=" * 80)
        lines.append(f"                       MARKET SNAPSHOT - {today}")
        lines.append("=" * 80)
        lines.append("")

        # Format indices section
        indices = snapshot.get("indices", [])
        if indices:
            lines.append(self._format_snapshot_indices(indices))
            lines.append("")

        # Format commodities and sectors side by side
        commodities = snapshot.get("commodities", [])
        sectors = snapshot.get("sectors", [])
        if commodities or sectors:
            lines.append(self._format_commodities_sectors(commodities, sectors))
            lines.append("")

        # Format bonds section
        bonds = snapshot.get("bonds", {})
        if bonds:
            lines.append(self._format_snapshot_bonds(bonds))
            lines.append("")

        # Footer
        now = datetime.now().strftime("%I:%M %p ET")
        lines.append(f"[dim]Last updated: {now} | SNAP to refresh[/dim]")

        return "\n".join(lines)

    def _format_snapshot_indices(self, quotes: list[Quote]) -> str:
        """Format indices in compact snapshot format."""
        # Separate by region
        us_symbols = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
        eu_symbols = ["^FTSE", "^GDAXI", "^FCHI"]
        asia_symbols = ["^N225", "^HSI", "^KS11"]

        us_indices = [q for q in quotes if q.symbol in us_symbols]
        eu_indices = [q for q in quotes if q.symbol in eu_symbols]
        asia_indices = [q for q in quotes if q.symbol in asia_symbols]

        def format_compact_index(q: Quote, short_name: str) -> str:
            """Format a single index compactly."""
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            pct = f"{sign}{q.change_percent:.2f}%"
            return f"{short_name} [{change_color}]{pct}[/{change_color}]"

        lines = []
        lines.append("EQUITY INDICES (1D)")
        lines.append("-" * 20)

        # US line
        us_parts = []
        name_map = {"^GSPC": "S&P 500", "^DJI": "Dow", "^IXIC": "NASDAQ", "^RUT": "Russell"}
        for q in us_indices:
            short_name = name_map.get(q.symbol, q.symbol)
            us_parts.append(format_compact_index(q, short_name))
        if us_parts:
            lines.append("US:   " + "   ".join(us_parts))

        # EU line
        eu_parts = []
        eu_name_map = {"^FTSE": "FTSE 100", "^GDAXI": "DAX", "^FCHI": "CAC 40"}
        for q in eu_indices:
            short_name = eu_name_map.get(q.symbol, q.symbol)
            eu_parts.append(format_compact_index(q, short_name))
        if eu_parts:
            lines.append("EU:   " + "   ".join(eu_parts))

        # Asia line
        asia_parts = []
        asia_name_map = {"^N225": "Nikkei", "^HSI": "Hang Seng", "^KS11": "KOSPI"}
        for q in asia_indices:
            short_name = asia_name_map.get(q.symbol, q.symbol)
            asia_parts.append(format_compact_index(q, short_name))
        if asia_parts:
            lines.append("ASIA: " + "   ".join(asia_parts))

        return "\n".join(lines)

    def _format_commodities_sectors(self, commodities: list[Quote], sectors: list[Quote]) -> str:
        """Format commodities and sectors in two-column layout."""
        lines = []

        # Build left column (commodities)
        left_lines = []
        left_lines.append("COMMODITIES (1D)")
        left_lines.append("-" * 18)
        for q in commodities:
            name = COMMODITY_NAMES.get(q.symbol, q.symbol)
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            pct = f"{sign}{q.change_percent:.2f}%"
            left_lines.append(f"{name} ({q.symbol}){' ' * (12 - len(name))}[{change_color}]{pct:>7}[/{change_color}]")

        # Build right column (sectors)
        right_lines = []
        right_lines.append("SECTORS (1D)")
        right_lines.append("-" * 15)
        for q in sectors:
            name = SECTOR_NAMES.get(q.symbol, q.symbol)
            change_color = "green" if q.change_percent >= 0 else "red"
            sign = "+" if q.change_percent >= 0 else ""
            pct = f"{sign}{q.change_percent:.1f}%"
            right_lines.append(f"{name} ({q.symbol}){' ' * (14 - len(name))}[{change_color}]{pct:>6}[/{change_color}]")

        # Combine columns
        max_lines = max(len(left_lines), len(right_lines))
        left_width = 30

        for i in range(max_lines):
            left = left_lines[i] if i < len(left_lines) else ""
            right = right_lines[i] if i < len(right_lines) else ""
            # Pad left column to fixed width (without markup)
            lines.append(f"{left:<{left_width}}    {right}")

        return "\n".join(lines)

    def _format_snapshot_bonds(self, bonds: dict) -> str:
        """Format bond yields in compact snapshot format."""
        lines = []
        lines.append("BOND YIELDS")
        lines.append("-" * 11)

        # Key alternatives for matching FMP response
        key_alternatives = {
            "2Y": ["year2", "twoYear", "2Y", "y2", "year_2", "2year"],
            "5Y": ["year5", "fiveYear", "5Y", "y5", "year_5", "5year"],
            "10Y": ["year10", "tenYear", "10Y", "y10", "year_10", "10year"],
            "30Y": ["year30", "thirtyYear", "30Y", "y30", "year_30", "30year"],
        }

        # Helper to find value for a maturity
        def get_yield(label: str) -> float | None:
            for key in key_alternatives.get(label, []):
                if key in bonds and bonds[key] is not None:
                    return bonds[key]
            return None

        # US Treasury line
        parts = []
        for label in ["2Y", "5Y", "10Y", "30Y"]:
            value = get_yield(label)
            if value is not None:
                parts.append(f"{label} {value:.2f}%")

        if parts:
            lines.append("US Treasury:  " + "   ".join(parts))

        # Calculate spread (10Y - 2Y)
        y2 = get_yield("2Y")
        y10 = get_yield("10Y")
        if y2 is not None and y10 is not None:
            spread = y10 - y2
            spread_color = "green" if spread >= 0 else "red"
            sign = "+" if spread >= 0 else ""
            lines.append(f"Spread (10Y-2Y): [{spread_color}]{sign}{spread:.2f}%[/{spread_color}]")

        return "\n".join(lines)

    def format_indices(self, quotes: list[Quote]) -> Union[str, RenderableType]:
        """Format world indices for display."""
        if not quotes:
            return "[dim]No index data available.[/dim]"

        # Separate by region (in display order)
        us_symbols = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
        europe_symbols = ["^FTSE", "^GDAXI", "^FCHI", "^STOXX50E", "^IBEX", "^AEX"]
        asia_symbols = ["^N225", "^HSI", "^KS11", "^AXJO", "^BSESN", "^TWII", "^STI"]

        def get_indices_for_region(symbols: list[str]) -> list[Optional[Quote]]:
            """Get indices in the order specified by symbols list."""
            result = []
            for symbol in symbols:
                quote = next((q for q in quotes if q.symbol == symbol), None)
                result.append(quote)
            return result

        us_indices = get_indices_for_region(us_symbols)
        europe_indices = get_indices_for_region(europe_symbols)
        asia_indices = get_indices_for_region(asia_symbols)

        def format_change(value: float) -> Text:
            """Format a percentage change with color."""
            style = "green" if value >= 0 else "red"
            sign = "+" if value >= 0 else ""
            return Text(f"{sign}{value:.2f}%", style=style)

        # Create table with 3 regions side by side
        table = Table(
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="bold yellow",
        )

        table.add_column("US Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)
        table.add_column("EU Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)
        table.add_column("Asia Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)

        # Build rows - one index from each region per row
        max_rows = max(len(us_indices), len(europe_indices), len(asia_indices))

        for i in range(max_rows):
            row = []

            # US column
            if i < len(us_indices) and us_indices[i]:
                q = us_indices[i]
                row.append(self.INDEX_NAMES.get(q.symbol, q.symbol))
                row.append(format_change(q.change_percent))
            else:
                row.extend(["", ""])

            # EU column
            if i < len(europe_indices) and europe_indices[i]:
                q = europe_indices[i]
                row.append(self.INDEX_NAMES.get(q.symbol, q.symbol))
                row.append(format_change(q.change_percent))
            else:
                row.extend(["", ""])

            # Asia column
            if i < len(asia_indices) and asia_indices[i]:
                q = asia_indices[i]
                row.append(self.INDEX_NAMES.get(q.symbol, q.symbol))
                row.append(format_change(q.change_percent))
            else:
                row.extend(["", ""])

            table.add_row(*row)

        return table

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

        # Map display labels to possible FMP key names
        key_alternatives = {
            "1M": ["month1", "oneMonth", "1M", "m1", "month_1", "1month"],
            "3M": ["month3", "threeMonth", "3M", "m3", "month_3", "3month"],
            "6M": ["month6", "sixMonth", "6M", "m6", "month_6", "6month"],
            "1Y": ["year1", "oneYear", "1Y", "y1", "year_1", "1year"],
            "2Y": ["year2", "twoYear", "2Y", "y2", "year_2", "2year"],
            "5Y": ["year5", "fiveYear", "5Y", "y5", "year_5", "5year"],
            "10Y": ["year10", "tenYear", "10Y", "y10", "year_10", "10year"],
            "30Y": ["year30", "thirtyYear", "30Y", "y30", "year_30", "30year"],
        }
        maturity_order = ["1M", "3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]

        # Build yield curve data
        yields = []
        labels = []
        matched_keys = {}  # Track which API keys matched which labels
        for label in maturity_order:
            for fmp_key in key_alternatives[label]:
                value = current.get(fmp_key)
                if value is not None:
                    yields.append(value)
                    labels.append(label)
                    matched_keys[label] = fmp_key
                    break

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

        # Display names for each maturity
        maturity_names = {
            "1M": "1 Month", "3M": "3 Month", "6M": "6 Month",
            "1Y": "1 Year", "2Y": "2 Year", "5Y": "5 Year",
            "10Y": "10 Year", "30Y": "30 Year",
        }

        for label in maturity_order:
            name = maturity_names[label]
            if label in matched_keys:
                fmp_key = matched_keys[label]
                value = current.get(fmp_key)
                # Calculate change if previous data available
                if previous and previous.get(fmp_key) is not None:
                    prev_value = previous.get(fmp_key)
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

    def format_forex(self, quotes: list[Quote]) -> Union[str, RenderableType]:
        """Format currency ETF quotes for display."""
        if not quotes:
            return "[dim]No currency data available.[/dim]"

        def format_change(value: float) -> Text:
            """Format a percentage change with color."""
            style = "green" if value >= 0 else "red"
            sign = "+" if value >= 0 else ""
            return Text(f"{sign}{value:.2f}%", style=style)

        def format_volume(volume: int) -> str:
            """Format volume in human-readable form."""
            if volume >= 1e9:
                return f"{volume / 1e9:.1f}B"
            if volume >= 1e6:
                return f"{volume / 1e6:.1f}M"
            if volume >= 1e3:
                return f"{volume / 1e3:.1f}K"
            return f"{volume:,}"

        table = Table(
            box=None,
            padding=(0, 1),
            expand=True,
            row_styles=["on grey23", ""],
        )

        table.add_column("Symbol", style="bold yellow", width=8)
        table.add_column("Currency", width=14)
        table.add_column("Price", justify="right", width=10)
        table.add_column("1D", justify="right", width=8)
        table.add_column("Volume", justify="right", width=10)

        for q in quotes:
            currency_name = self.CURRENCY_ETF_NAMES.get(q.symbol, q.name[:12])
            table.add_row(
                q.symbol,
                currency_name,
                f"${q.price:.2f}",
                format_change(q.change_percent),
                format_volume(q.volume),
            )

        return table

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

    async def get_international_bond_snapshot(self) -> dict[str, dict]:
        """Get international bond yields snapshot.

        Returns:
            Dictionary mapping country code to yields dict.
            Example: {'US': {'1M': 4.50, '5Y': 4.15, '10Y': 4.28}, ...}
        """
        result = {}

        # Get US Treasury rates from FMP
        us_rates, _ = await self._fmp.get_treasury_rates()
        if us_rates:
            us_yields = {}
            # Map display labels to possible FMP key names
            key_alternatives = {
                "1M": ["month1", "oneMonth", "1M", "m1", "month_1", "1month"],
                "3M": ["month3", "threeMonth", "3M", "m3", "month_3", "3month"],
                "6M": ["month6", "sixMonth", "6M", "m6", "month_6", "6month"],
                "1Y": ["year1", "oneYear", "1Y", "y1", "year_1", "1year"],
                "2Y": ["year2", "twoYear", "2Y", "y2", "year_2", "2year"],
                "5Y": ["year5", "fiveYear", "5Y", "y5", "year_5", "5year"],
                "10Y": ["year10", "tenYear", "10Y", "y10", "year_10", "10year"],
                "30Y": ["year30", "thirtyYear", "30Y", "y30", "year_30", "30year"],
            }
            for label, possible_keys in key_alternatives.items():
                for fmp_key in possible_keys:
                    if fmp_key in us_rates and us_rates[fmp_key] is not None:
                        us_yields[label] = us_rates[fmp_key]
                        break
            if us_yields:
                result["US"] = us_yields

        # Get international yields from EODHD if available
        if self._eodhd:
            intl_snapshot = await self._eodhd.get_international_snapshot()
            result.update(intl_snapshot)

        return result

    async def get_country_bond_detail(self, country_code: str) -> Optional[dict]:
        """Get detailed bond yields for a specific country.

        Args:
            country_code: Two-letter country code (e.g., 'US', 'DE')

        Returns:
            Dictionary with country info and yields, or None if not found.
            Example: {
                'country': 'Germany',
                'code': 'DE',
                'yields': {
                    '10Y': {'yield': 2.45, 'change': 0.05},
                    ...
                }
            }
        """
        country_code = country_code.upper()

        if country_code == "US":
            return await self._get_us_bond_detail()
        elif country_code in COUNTRY_BONDS:
            return await self._get_intl_bond_detail(country_code)
        else:
            return None

    async def _get_us_bond_detail(self) -> dict:
        """Get US Treasury bond detail from FMP."""
        current, previous = await self._fmp.get_treasury_rates()

        yields = {}
        # Map from display label to possible FMP key names
        # FMP API may use different naming conventions
        key_alternatives = {
            "1M": ["month1", "oneMonth", "1M", "m1", "month_1", "1month"],
            "3M": ["month3", "threeMonth", "3M", "m3", "month_3", "3month"],
            "6M": ["month6", "sixMonth", "6M", "m6", "month_6", "6month"],
            "1Y": ["year1", "oneYear", "1Y", "y1", "year_1", "1year"],
            "2Y": ["year2", "twoYear", "2Y", "y2", "year_2", "2year"],
            "5Y": ["year5", "fiveYear", "5Y", "y5", "year_5", "5year"],
            "10Y": ["year10", "tenYear", "10Y", "y10", "year_10", "10year"],
            "30Y": ["year30", "thirtyYear", "30Y", "y30", "year_30", "30year"],
        }

        for label, possible_keys in key_alternatives.items():
            for fmp_key in possible_keys:
                if fmp_key in current and current[fmp_key] is not None:
                    yield_val = current[fmp_key]
                    change = None
                    if previous and fmp_key in previous and previous[fmp_key] is not None:
                        change = yield_val - previous[fmp_key]
                    yields[label] = {"yield": yield_val, "change": change}
                    break  # Found a match, move to next maturity

        return {
            "country": "United States",
            "code": "US",
            "yields": yields,
        }

    async def _get_intl_bond_detail(self, country_code: str) -> Optional[dict]:
        """Get international bond detail from EODHD."""
        if not self._eodhd:
            return None

        country_info = COUNTRY_BONDS.get(country_code)
        if not country_info:
            return None

        raw_yields = await self._eodhd.get_country_yields(country_code)

        yields = {}
        for maturity, data in raw_yields.items():
            yield_val = data.get("close")
            change = data.get("change")
            if yield_val is not None:
                yields[maturity] = {"yield": yield_val, "change": change}

        return {
            "country": country_info["name"],
            "code": country_code,
            "yields": yields,
        }

    def format_international_bond_snapshot(self, snapshot: dict) -> str:
        """Format international bond snapshot for display."""
        if not snapshot:
            return "[dim]No bond data available.[/dim]"

        lines = []
        lines.append("=" * 70)
        lines.append("              INTERNATIONAL GOVERNMENT BOND YIELDS")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"{'Country':<25}   {'1M':>6}   {'5Y':>6}   {'10Y':>6}")
        lines.append("-" * 25 + "   " + "-" * 6 + "   " + "-" * 6 + "   " + "-" * 6)

        # Order countries: US first, then alphabetically by name
        ordered_codes = ["US"] + [
            code for code in sorted(
                snapshot.keys(),
                key=lambda c: COUNTRY_NAMES.get(c, c)
            )
            if code != "US"
        ]

        for code in ordered_codes:
            if code not in snapshot:
                continue
            yields = snapshot[code]
            country_name = COUNTRY_NAMES.get(code, code)
            display_name = f"{country_name} ({code})"

            val_1m = yields.get("1M")
            val_5y = yields.get("5Y")
            val_10y = yields.get("10Y")

            str_1m = f"{val_1m:.2f}" if val_1m is not None else "-"
            str_5y = f"{val_5y:.2f}" if val_5y is not None else "-"
            str_10y = f"{val_10y:.2f}" if val_10y is not None else "-"

            lines.append(
                f"{display_name:<25}   {str_1m:>6}   {str_5y:>6}   {str_10y:>6}"
            )

        lines.append("")
        lines.append("[dim]Source: FMP (US), EODHD (Intl) | WB <CODE> for detail[/dim]")

        return "\n".join(lines)

    def format_country_bond_detail(self, detail: Optional[dict]) -> str:
        """Format country bond detail for display."""
        if not detail:
            return "[dim]No bond data available for this country.[/dim]"

        country = detail["country"]
        yields = detail["yields"]

        lines = []
        lines.append("=" * 65)
        lines.append(f"             {country.upper()} GOVERNMENT BOND YIELDS")
        lines.append("=" * 65)
        lines.append("")

        # Get ordered maturities
        maturity_order = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
        ordered_mats = [m for m in maturity_order if m in yields]

        # Build yield curve data for chart
        curve_yields = []
        curve_labels = []
        for mat in ordered_mats:
            yield_val = yields[mat].get("yield")
            if yield_val is not None:
                curve_yields.append(yield_val)
                curve_labels.append(mat)

        # Render yield curve
        if len(curve_yields) >= 2:
            lines.append("[bold]Yield Curve[/bold]")
            lines.append("")

            min_yield = min(curve_yields)
            max_yield = max(curve_yields)
            chart_height = 8

            if max_yield > min_yield:
                normalized = [
                    (y - min_yield) / (max_yield - min_yield) * (chart_height - 1)
                    for y in curve_yields
                ]
            else:
                normalized = [chart_height // 2] * len(curve_yields)

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

            lines.append("       +" + "-------" * len(curve_labels))
            axis_labels = "        "
            for label in curve_labels:
                axis_labels += f"{label:^7}"
            lines.append(axis_labels)
            lines.append("")

        # Maturity table
        maturity_display = {
            "1M": "1 Month", "3M": "3 Month", "6M": "6 Month",
            "1Y": "1 Year", "2Y": "2 Year", "3Y": "3 Year",
            "5Y": "5 Year", "7Y": "7 Year", "10Y": "10 Year",
            "20Y": "20 Year", "30Y": "30 Year",
        }

        lines.append("Maturity        Yield      Change")
        lines.append("-" * 14 + "  " + "-" * 7 + "  " + "-" * 10)

        for mat in ordered_mats:
            yield_info = yields[mat]
            yield_val = yield_info.get("yield")
            change = yield_info.get("change")

            display_name = maturity_display.get(mat, mat)

            if yield_val is not None:
                if change is not None:
                    change_bp = change * 100
                    change_color = "green" if change_bp >= 0 else "red"
                    sign = "+" if change_bp >= 0 else ""
                    bp_str = f"{sign}{change_bp:.1f}bp"
                    change_str = f"[{change_color}]{bp_str:>10}[/{change_color}]"
                else:
                    change_str = "[dim]       N/A[/dim]"
                lines.append(f"{display_name:<14}  {yield_val:>6.2f}%  {change_str}")
            else:
                lines.append(f"{display_name:<14}  [dim]   N/A[/dim]  [dim]       N/A[/dim]")

        return "\n".join(lines)
