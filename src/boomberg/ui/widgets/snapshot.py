"""Market snapshot widget for displaying consolidated market overview."""

from datetime import datetime
from typing import Optional

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from boomberg.api.models import Quote
from boomberg.services.dashboard import COMMODITY_NAMES, SECTOR_NAMES


class SnapshotWidget(Static):
    """Widget for displaying market snapshot."""

    DEFAULT_CSS = """
    SnapshotWidget {
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
        self._indices: list[Quote] = []
        self._commodities: list[Quote] = []
        self._sectors: list[Quote] = []
        self._bonds: dict = {}
        self._last_updated: Optional[datetime] = None

    def update_snapshot(
        self,
        indices: list[Quote],
        commodities: list[Quote],
        sectors: list[Quote],
        bonds: dict,
    ) -> None:
        """Update the snapshot data."""
        self._indices = indices
        self._commodities = commodities
        self._sectors = sectors
        self._bonds = bonds
        self._last_updated = datetime.now()
        self.refresh()

    def render(self) -> RenderableType:
        """Render the market snapshot."""
        today = datetime.now().strftime("%b %d, %Y")
        self.border_title = f"Market Snapshot - {today}"

        if not self._indices and not self._commodities and not self._sectors:
            return Text("Loading market snapshot...", style="dim italic")

        # Create sections
        sections = []

        # Indices table
        if self._indices:
            sections.append(self._render_indices())
            sections.append(Text(""))

        # Side-by-side commodities and sectors
        if self._commodities or self._sectors:
            sections.append(self._render_commodities_sectors())
            sections.append(Text(""))

        # Bonds table
        if self._bonds:
            sections.append(self._render_bonds())
            sections.append(Text(""))

        # Footer
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p ET")
            sections.append(Text(f"Last updated: {updated_time} | SNAP to refresh", style="dim"))

        return Group(*sections)

    def _render_indices(self) -> Table:
        """Render indices as a table with regions side by side."""
        table = Table(
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="bold yellow",
        )

        # Three regions side by side, matching commodity/sector layout
        table.add_column("US Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)
        table.add_column("EU Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)
        table.add_column("Asia Equities", ratio=1)
        table.add_column("1D", justify="right", width=8)

        # Group indices by region
        us_symbols = ["^GSPC", "^DJI", "^IXIC", "^RUT"]
        eu_symbols = ["^FTSE", "^GDAXI", "^FCHI", "^STOXX50E"]
        asia_symbols = ["^N225", "^HSI", "^KS11", "^AXJO"]

        name_map = {
            "^GSPC": "S&P 500", "^DJI": "Dow Jones", "^IXIC": "NASDAQ", "^RUT": "Russell 2000",
            "^FTSE": "FTSE 100", "^GDAXI": "DAX", "^FCHI": "CAC 40", "^STOXX50E": "Euro STOXX",
            "^N225": "Nikkei 225", "^HSI": "Hang Seng", "^KS11": "KOSPI", "^AXJO": "ASX 200",
        }

        def get_indices_for_region(symbols: list[str]) -> list[Optional[Quote]]:
            """Get indices in the order specified by symbols list."""
            result = []
            for symbol in symbols:
                quote = next((q for q in self._indices if q.symbol == symbol), None)
                result.append(quote)
            return result

        us_indices = get_indices_for_region(us_symbols)
        eu_indices = get_indices_for_region(eu_symbols)
        asia_indices = get_indices_for_region(asia_symbols)

        # Build rows - one index from each region per row
        max_rows = max(len(us_indices), len(eu_indices), len(asia_indices))

        for i in range(max_rows):
            row = []

            # US column
            if i < len(us_indices) and us_indices[i]:
                q = us_indices[i]
                row.append(name_map.get(q.symbol, q.symbol))
                row.append(self._format_change(q.change_percent))
            else:
                row.extend(["", ""])

            # EU column
            if i < len(eu_indices) and eu_indices[i]:
                q = eu_indices[i]
                row.append(name_map.get(q.symbol, q.symbol))
                row.append(self._format_change(q.change_percent))
            else:
                row.extend(["", ""])

            # Asia column
            if i < len(asia_indices) and asia_indices[i]:
                q = asia_indices[i]
                row.append(name_map.get(q.symbol, q.symbol))
                row.append(self._format_change(q.change_percent))
            else:
                row.extend(["", ""])

            table.add_row(*row)

        return table

    def _render_commodities_sectors(self) -> Table:
        """Render commodities and sectors side by side."""
        table = Table(
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="bold yellow",
        )

        # Use ratio for balanced columns, no spacer needed
        table.add_column("Commodity", ratio=1)
        table.add_column("1D", justify="right", width=8)
        table.add_column("Sector", ratio=1)
        table.add_column("1D", justify="right", width=8)

        max_rows = max(len(self._commodities), len(self._sectors))

        for i in range(max_rows):
            row = []

            # Commodity column
            if i < len(self._commodities):
                q = self._commodities[i]
                name = COMMODITY_NAMES.get(q.symbol, q.symbol)
                row.append(f"{name} ({q.symbol})")
                row.append(self._format_change(q.change_percent))
            else:
                row.extend(["", ""])

            # Sector column
            if i < len(self._sectors):
                q = self._sectors[i]
                name = SECTOR_NAMES.get(q.symbol, q.symbol)
                row.append(f"{name} ({q.symbol})")
                row.append(self._format_change(q.change_percent))
            else:
                row.extend(["", ""])

            table.add_row(*row)

        return table

    def _render_bonds(self) -> Table:
        """Render bond yields."""
        table = Table(
            title="US Treasury Yields",
            title_style="bold yellow",
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="dim",
        )

        # Use ratio for balanced, expanded columns
        table.add_column("2Y", justify="center", ratio=1)
        table.add_column("5Y", justify="center", ratio=1)
        table.add_column("10Y", justify="center", ratio=1)
        table.add_column("30Y", justify="center", ratio=1)
        table.add_column("Spread (10Y-2Y)", justify="center", ratio=1)

        # Key alternatives for matching FMP response
        key_alternatives = {
            "2Y": ["year2", "twoYear", "2Y", "y2", "year_2", "2year"],
            "5Y": ["year5", "fiveYear", "5Y", "y5", "year_5", "5year"],
            "10Y": ["year10", "tenYear", "10Y", "y10", "year_10", "10year"],
            "30Y": ["year30", "thirtyYear", "30Y", "y30", "year_30", "30year"],
        }

        def get_yield(label: str) -> float | None:
            for key in key_alternatives.get(label, []):
                if key in self._bonds and self._bonds[key] is not None:
                    return self._bonds[key]
            return None

        y2 = get_yield("2Y")
        y5 = get_yield("5Y")
        y10 = get_yield("10Y")
        y30 = get_yield("30Y")

        # Calculate spread
        spread_text = Text("-")
        if y2 is not None and y10 is not None:
            spread = y10 - y2
            style = "green" if spread >= 0 else "red"
            sign = "+" if spread >= 0 else ""
            spread_text = Text(f"{sign}{spread:.2f}%", style=style)

        table.add_row(
            f"{y2:.2f}%" if y2 is not None else "-",
            f"{y5:.2f}%" if y5 is not None else "-",
            f"{y10:.2f}%" if y10 is not None else "-",
            f"{y30:.2f}%" if y30 is not None else "-",
            spread_text,
        )

        return table

    def _format_change(self, value: float) -> Text:
        """Format a percentage change with color."""
        style = "green" if value >= 0 else "red"
        sign = "+" if value >= 0 else ""
        return Text(f"{sign}{value:.2f}%", style=style)
