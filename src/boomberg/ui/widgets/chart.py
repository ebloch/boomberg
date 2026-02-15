"""Chart widget using plotext for terminal rendering."""

from typing import Optional

import plotext as plt
from rich.console import RenderableType
from rich.text import Text
from textual.widgets import Static

from boomberg.api.models import HistoricalPrice


class ChartWidget(Static):
    """Widget for displaying price charts using plotext."""

    DEFAULT_CSS = """
    ChartWidget {
        width: 100%;
        height: 20;
        padding: 0;
        background: $surface;
        border: solid $primary;
    }
    """

    def __init__(
        self,
        symbol: str = "",
        period: str = "1M",
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._symbol = symbol
        self._period = period
        self._prices: list[HistoricalPrice] = []
        self._chart_type: str = "line"  # 'line' or 'candlestick'

    def update_data(
        self,
        symbol: str,
        prices: list[HistoricalPrice],
        period: str = "1M",
    ) -> None:
        """Update chart data."""
        self._symbol = symbol
        self._prices = prices
        self._period = period
        self.refresh()

    def set_chart_type(self, chart_type: str) -> None:
        """Set chart type: 'line' or 'candlestick'."""
        if chart_type in ("line", "candlestick"):
            self._chart_type = chart_type
            self.refresh()

    def render(self) -> RenderableType:
        """Render the chart."""
        if not self._prices:
            return Text(
                "No chart data. Use GP <SYMBOL> to view a price chart.",
                style="dim italic",
            )

        # Prepare data (prices come newest first, reverse for chronological order)
        prices = list(reversed(self._prices))
        closes = [p.close for p in prices]

        # Use numeric indices for x-axis to avoid date parsing issues
        x_indices = list(range(len(prices)))

        # Create date labels for x-axis ticks (show a subset to avoid crowding)
        date_labels = [p.date.strftime("%m/%d") for p in prices]

        # Calculate dimensions based on widget size
        width = max(60, self.size.width - 4) if self.size.width > 0 else 80
        height = max(10, self.size.height - 2) if self.size.height > 0 else 15

        # Clear previous plot
        plt.clf()
        plt.plotsize(width, height)

        if self._chart_type == "candlestick" and len(prices) > 1:
            # Candlestick chart using numeric indices
            opens = [p.open for p in prices]
            highs = [p.high for p in prices]
            lows = [p.low for p in prices]
            plt.candlestick(x_indices, {"Open": opens, "Close": closes, "High": highs, "Low": lows})
        else:
            # Line chart
            plt.plot(x_indices, closes, marker="braille")

        # Set x-axis labels (show every nth label to avoid crowding)
        if len(date_labels) > 10:
            step = len(date_labels) // 8
            tick_indices = x_indices[::step]
            tick_labels = date_labels[::step]
        else:
            tick_indices = x_indices
            tick_labels = date_labels

        plt.xticks(tick_indices, tick_labels)

        # Configure appearance
        plt.title(f"{self._symbol} - {self._period}")
        plt.xlabel("Date")
        plt.ylabel("Price ($)")
        plt.theme("dark")

        # Render to string using build()
        chart_str = plt.build()

        return Text.from_ansi(chart_str)
