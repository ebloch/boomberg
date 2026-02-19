"""Bonds widget for displaying international bond yields."""

from datetime import datetime
from typing import Optional

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.widgets import Static

from boomberg.services.dashboard import COUNTRY_NAMES


class BondsWidget(Static):
    """Widget for displaying bond yields."""

    DEFAULT_CSS = """
    BondsWidget {
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
        self._snapshot: Optional[dict] = None
        self._detail: Optional[dict] = None
        self._last_updated: Optional[datetime] = None

    def update_snapshot(self, snapshot: dict) -> None:
        """Update with international bond snapshot data."""
        self._snapshot = snapshot
        self._detail = None
        self._last_updated = datetime.now()
        self.refresh()

    def update_detail(self, detail: dict) -> None:
        """Update with country bond detail data."""
        self._detail = detail
        self._snapshot = None
        self._last_updated = datetime.now()
        self.refresh()

    def render(self) -> RenderableType:
        """Render the bonds widget."""
        if self._detail:
            return self._render_detail()
        elif self._snapshot:
            return self._render_snapshot()
        else:
            return Text("Loading bond data...", style="dim italic")

    def _render_snapshot(self) -> RenderableType:
        """Render international bond snapshot."""
        self.border_title = "International Government Bond Yields"

        if not self._snapshot:
            return Text("No bond data available.", style="dim italic")

        table = Table(
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="bold yellow",
            row_styles=["on grey23", ""],
        )

        table.add_column("Country", ratio=1)
        table.add_column("1M", justify="right", width=8)
        table.add_column("5Y", justify="right", width=8)
        table.add_column("10Y", justify="right", width=8)

        # Order countries: US first, then alphabetically by name
        ordered_codes = ["US"] + [
            code for code in sorted(
                self._snapshot.keys(),
                key=lambda c: COUNTRY_NAMES.get(c, c)
            )
            if code != "US"
        ]

        for code in ordered_codes:
            if code not in self._snapshot:
                continue
            yields = self._snapshot[code]
            country_name = COUNTRY_NAMES.get(code, code)
            display_name = f"{country_name} ({code})"

            val_1m = yields.get("1M")
            val_5y = yields.get("5Y")
            val_10y = yields.get("10Y")

            str_1m = f"{val_1m:.2f}%" if val_1m is not None else "-"
            str_5y = f"{val_5y:.2f}%" if val_5y is not None else "-"
            str_10y = f"{val_10y:.2f}%" if val_10y is not None else "-"

            table.add_row(display_name, str_1m, str_5y, str_10y)

        sections = [table]
        sections.append(Text(""))

        footer_parts = []
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p")
            footer_parts.append(f"Last updated: {updated_time}")
        footer_parts.append("WB to refresh")
        footer_parts.append("WB <CODE> for detail")

        sections.append(Text(" | ".join(footer_parts), style="dim"))

        return Group(*sections)

    def _render_detail(self) -> RenderableType:
        """Render country bond detail."""
        if not self._detail:
            return Text("No bond data available.", style="dim italic")

        country = self._detail.get("country", "Unknown")
        code = self._detail.get("code", "")
        yields = self._detail.get("yields", {})

        self.border_title = f"{country} Government Bond Yields"

        sections = []

        # Yield curve visualization
        maturity_order = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]
        ordered_mats = [m for m in maturity_order if m in yields]

        curve_yields = []
        curve_labels = []
        for mat in ordered_mats:
            yield_val = yields[mat].get("yield")
            if yield_val is not None:
                curve_yields.append(yield_val)
                curve_labels.append(mat)

        if len(curve_yields) >= 2:
            sections.append(Text("Yield Curve", style="bold"))
            sections.append(Text(""))
            sections.append(self._render_yield_curve(curve_yields, curve_labels))
            sections.append(Text(""))

        # Yields table
        table = Table(
            box=None,
            padding=(0, 2),
            expand=True,
            show_header=True,
            header_style="bold yellow",
            row_styles=["on grey23", ""],
        )

        table.add_column("Maturity", width=12)
        table.add_column("Yield", justify="right", width=10)
        table.add_column("Change", justify="right", width=12)

        maturity_display = {
            "1M": "1 Month", "3M": "3 Month", "6M": "6 Month",
            "1Y": "1 Year", "2Y": "2 Year", "3Y": "3 Year",
            "5Y": "5 Year", "7Y": "7 Year", "10Y": "10 Year",
            "20Y": "20 Year", "30Y": "30 Year",
        }

        for mat in ordered_mats:
            yield_info = yields[mat]
            yield_val = yield_info.get("yield")
            change = yield_info.get("change")

            display_name = maturity_display.get(mat, mat)

            if yield_val is not None:
                yield_text = f"{yield_val:.2f}%"
                if change is not None:
                    change_bp = change * 100
                    style = "green" if change_bp >= 0 else "red"
                    sign = "+" if change_bp >= 0 else ""
                    change_text = Text(f"{sign}{change_bp:.1f}bp", style=style)
                else:
                    change_text = Text("-", style="dim")
                table.add_row(display_name, yield_text, change_text)
            else:
                table.add_row(display_name, "-", "-")

        sections.append(table)
        sections.append(Text(""))

        footer_parts = []
        if self._last_updated:
            updated_time = self._last_updated.strftime("%I:%M %p")
            footer_parts.append(f"Last updated: {updated_time}")
        footer_parts.append(f"WB {code} to refresh")
        footer_parts.append("WB for overview")

        sections.append(Text(" | ".join(footer_parts), style="dim"))

        return Group(*sections)

    def _render_yield_curve(self, yields: list[float], labels: list[str]) -> Text:
        """Render ASCII yield curve."""
        if len(yields) < 2:
            return Text("")

        min_yield = min(yields)
        max_yield = max(yields)
        chart_height = 6

        lines = []

        if max_yield > min_yield:
            normalized = [
                (y - min_yield) / (max_yield - min_yield) * (chart_height - 1)
                for y in yields
            ]
        else:
            normalized = [chart_height // 2] * len(yields)

        for row in range(chart_height - 1, -1, -1):
            if row == chart_height - 1:
                label = f"{max_yield:.1f}%"
            elif row == 0:
                label = f"{min_yield:.1f}%"
            else:
                label = "     "

            line = f"{label:>6} |"
            for norm_val in normalized:
                if round(norm_val) == row:
                    line += "  *  "
                elif round(norm_val) > row:
                    line += "  |  "
                else:
                    line += "     "
            lines.append(line)

        # X-axis
        lines.append("       +" + "-----" * len(labels))
        axis_labels = "        "
        for label in labels:
            axis_labels += f"{label:^5}"
        lines.append(axis_labels)

        return Text("\n".join(lines))
