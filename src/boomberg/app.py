"""Main Boomberg application."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Static

from boomberg.api.client import FMPClient
from boomberg.api.exceptions import APIError, SymbolNotFoundError
from boomberg.api.fred_client import FREDClient
from boomberg.api.models import Quote
from boomberg.config import Settings, get_settings
from boomberg.services.dashboard import DashboardService
from boomberg.services.financials import FinancialsService
from boomberg.services.fundamentals import FundamentalsService
from boomberg.services.historical import HistoricalService
from boomberg.services.news import NewsService
from boomberg.services.quotes import QuoteService
from boomberg.services.search import SearchService
from boomberg.services.watchlist import WatchlistService
from boomberg.storage.watchlist_store import WatchlistStore
from boomberg.ui.widgets.chart import ChartWidget
from boomberg.ui.widgets.command_bar import CommandBar
from boomberg.ui.widgets.quote_panel import QuotePanel, get_currency_symbol
from boomberg.ui.widgets.ticker_tape import TickerTape
from boomberg.ui.widgets.watchlist import WatchlistWidget


class Boomberg(App):
    """Boomberg TUI Application."""

    TITLE = "Boomberg"
    CSS_PATH = Path(__file__).parent / "ui" / "styles" / "app.tcss"

    BINDINGS = [
        ("?", "show_help", "Help"),
        ("escape", "focus_command", "Command"),
        ("ctrl+w", "show_watchlist", "Watchlist"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, settings: Optional[Settings] = None):
        super().__init__()
        self._settings = settings or get_settings()
        self._client: Optional[FMPClient] = None
        self._fred_client: Optional[FREDClient] = None
        self._quote_service: Optional[QuoteService] = None
        self._watchlist_service: Optional[WatchlistService] = None
        self._historical_service: Optional[HistoricalService] = None
        self._fundamentals_service: Optional[FundamentalsService] = None
        self._financials_service: Optional[FinancialsService] = None
        self._news_service: Optional[NewsService] = None
        self._search_service: Optional[SearchService] = None
        self._dashboard_service: Optional[DashboardService] = None
        self._current_symbol: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield TickerTape(id="ticker-tape")
        yield Container(
            Vertical(
                QuotePanel(id="quote-panel"),
                ChartWidget(id="chart-widget"),
                WatchlistWidget(id="watchlist-widget"),
                VerticalScroll(
                    Static(id="content-area"),
                    id="content-scroll",
                ),
                id="main-content",
            ),
            id="main-container",
        )
        yield CommandBar(id="command-bar")
        yield Footer()

    async def on_mount(self) -> None:
        """Initialize services when app mounts."""
        self._client = FMPClient(self._settings)
        await self._client.__aenter__()

        # Initialize FRED client if API key is configured
        if self._settings.fred_api_key:
            self._fred_client = FREDClient(self._settings)
            await self._fred_client.__aenter__()

        store = WatchlistStore(self._settings.watchlist_path)
        self._quote_service = QuoteService(self._client)
        self._watchlist_service = WatchlistService(self._client, store)
        self._historical_service = HistoricalService(self._client)
        self._fundamentals_service = FundamentalsService(self._client)
        self._financials_service = FinancialsService(self._client)
        self._news_service = NewsService(self._client)
        self._search_service = SearchService(self._client)
        self._dashboard_service = DashboardService(self._client, self._fred_client)

        # Focus command bar
        self.query_one(CommandBar).focus_input()

        # Load initial watchlist for ticker
        self._load_ticker_data()

        # Auto-refresh ticker every 5 minutes
        self.set_interval(300, self._load_ticker_data)

        # Hide widgets initially
        self.query_one("#chart-widget").display = False
        self.query_one("#watchlist-widget").display = False
        self.query_one("#content-scroll").display = False

    async def on_unmount(self) -> None:
        """Clean up when app unmounts."""
        if self._fred_client:
            await self._fred_client.__aexit__(None, None, None)
        if self._client:
            await self._client.__aexit__(None, None, None)

    def get_system_commands(self, screen) -> list[SystemCommand]:
        """Override to reorder system commands with Quit at the end."""
        for cmd in super().get_system_commands(screen):
            if cmd.title.lower() == "quit":
                # Rename to sort last alphabetically (~ comes after letters)
                yield SystemCommand("~Quit", cmd.help, cmd.callback, cmd.discover)
            else:
                yield cmd

    @work(exclusive=True)
    async def _load_ticker_data(self) -> None:
        """Load ticker tape data from watchlist."""
        try:
            symbols = await self._watchlist_service.get_watchlist("default")
            if symbols:
                quotes = await self._quote_service.get_quotes(symbols[:10])
                self.query_one(TickerTape).update_quotes(quotes)
        except Exception:
            pass  # Silently fail for ticker

    @on(CommandBar.CommandSubmitted)
    def handle_command(self, event: CommandBar.CommandSubmitted) -> None:
        """Handle commands from the command bar."""
        command = event.command
        args = event.args

        # Refresh ticker on each command
        self._load_ticker_data()

        if command == "Q" and args:
            self._show_quote(args[0])
        elif command == "GP" and args:
            period = args[1] if len(args) > 1 else "1M"
            self._show_chart(args[0], period)
        elif command == "FA" and args:
            self._show_fundamentals(args[0])
        elif command == "FI" and args:
            self._show_financials(args[0])
        elif command == "IS" and args:
            years, quarterly = self._parse_statement_args(args[1:])
            self._show_income_statement(args[0], years, quarterly)
        elif command == "BS" and args:
            years, quarterly = self._parse_statement_args(args[1:])
            self._show_balance_sheet(args[0], years, quarterly)
        elif command == "CF" and args:
            years, quarterly = self._parse_statement_args(args[1:])
            self._show_cash_flow(args[0], years, quarterly)
        elif command == "N":
            symbol = args[0] if args else None
            self._show_news(symbol)
        elif command == "W":
            self._show_watchlist()
        elif command == "WA" and args:
            self._add_to_watchlist(args[0])
        elif command == "WD" and args:
            self._remove_from_watchlist(args[0])
        elif command == "S" and args:
            self._search_symbols(" ".join(args))
        elif command == "WEI":
            self._show_world_indices()
        elif command == "TOP":
            self._show_top_news()
        elif command == "MOST":
            self._show_most_active()
        elif command == "WB":
            self._show_treasury_rates()
        elif command == "FXIP":
            self._show_forex()
        elif command == "ECST":
            self._show_economic_stats()
        elif command in ("?", "HELP"):
            self.action_show_help()
        else:
            self._show_message(f"Unknown command: {command}. Press ? for help.", error=True)

    @work(exclusive=True, group="quote")
    async def _show_quote(self, symbol: str) -> None:
        """Show quote for a symbol."""
        try:
            self._show_loading(f"Loading quote for {symbol}...")
            quote = await self._quote_service.get_quote(symbol)
            self._current_symbol = symbol.upper()

            quote_panel = self.query_one(QuotePanel)
            quote_panel.update_quote(quote)
            quote_panel.display = True

            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#content-scroll").display = False
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="chart")
    async def _show_chart(self, symbol: str, period: str = "1M") -> None:
        """Show price chart for a symbol."""
        try:
            self._show_loading(f"Loading chart for {symbol} ({period})...")
            prices = await self._historical_service.get_historical_prices_period(
                symbol, period
            )

            chart = self.query_one(ChartWidget)
            chart.update_data(symbol.upper(), prices, period)
            chart.display = True

            self.query_one(QuotePanel).display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#content-scroll").display = False
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="fundamentals")
    async def _show_fundamentals(self, symbol: str) -> None:
        """Show fundamentals for a symbol."""
        try:
            self._show_loading(f"Loading fundamentals for {symbol}...")
            profile = await self._fundamentals_service.get_profile(symbol)
            summary = self._fundamentals_service.get_profile_summary(profile)

            content = f"[bold cyan]Fundamentals: {symbol.upper()}[/bold cyan]\n\n"
            for key, value in summary.items():
                content += f"[yellow]{key}:[/yellow] {value}\n"

            if profile.description:
                content += f"\n[yellow]Description:[/yellow]\n{profile.description[:500]}..."

            self._show_content(content)
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="financials")
    async def _show_financials(self, symbol: str) -> None:
        """Show financial ratios and key metrics for a symbol."""
        try:
            self._show_loading(f"Loading financials for {symbol}...")

            # Fetch quote, ratios and metrics in parallel
            import asyncio
            quote, ratios, metrics, income = await asyncio.gather(
                self._client.get_quote(symbol),
                self._financials_service.get_ratios(symbol),
                self._financials_service.get_key_metrics(symbol),
                self._financials_service.get_income_statement(symbol, limit=1),
            )

            # Get currency symbol from exchange
            currency = get_currency_symbol(quote.exchange)

            content = f"[bold cyan]Financials: {symbol.upper()}[/bold cyan]\n"
            content += "=" * 50 + "\n\n"

            # Key Metrics section
            content += "[bold yellow]Key Metrics (TTM)[/bold yellow]\n"
            content += "-" * 30 + "\n"
            metrics_summary = self._financials_service.get_metrics_summary(metrics, currency)
            for key, value in metrics_summary.items():
                content += f"  {key:.<24} {value}\n"
            content += "\n"

            # Financial Ratios section
            content += "[bold yellow]Financial Ratios (TTM)[/bold yellow]\n"
            content += "-" * 30 + "\n"
            ratios_summary = self._financials_service.get_ratios_summary(ratios, metrics)

            # Group ratios by category
            profitability = ["Gross Margin", "Operating Margin", "Net Margin", "ROE", "ROA"]
            liquidity = ["Current Ratio", "Quick Ratio", "Cash Ratio"]
            valuation = ["P/E Ratio", "PEG Ratio", "P/B Ratio", "P/S Ratio"]
            debt = ["Debt Ratio", "D/E Ratio", "Interest Coverage"]
            dividend = ["Dividend Yield", "Payout Ratio"]

            content += "\n[cyan]Profitability[/cyan]\n"
            for key in profitability:
                content += f"  {key:.<24} {ratios_summary.get(key, 'N/A')}\n"

            content += "\n[cyan]Liquidity[/cyan]\n"
            for key in liquidity:
                content += f"  {key:.<24} {ratios_summary.get(key, 'N/A')}\n"

            content += "\n[cyan]Valuation[/cyan]\n"
            for key in valuation:
                content += f"  {key:.<24} {ratios_summary.get(key, 'N/A')}\n"

            content += "\n[cyan]Debt[/cyan]\n"
            for key in debt:
                content += f"  {key:.<24} {ratios_summary.get(key, 'N/A')}\n"

            content += "\n[cyan]Dividend[/cyan]\n"
            for key in dividend:
                content += f"  {key:.<24} {ratios_summary.get(key, 'N/A')}\n"

            # Latest Income Statement
            if income:
                content += "\n[bold yellow]Latest Income Statement[/bold yellow]\n"
                content += "-" * 30 + "\n"
                income_summary = self._financials_service.get_income_summary(income[0], currency)
                for key, value in income_summary.items():
                    content += f"  {key:.<24} {value}\n"

            self._show_content(content)
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    def _parse_statement_args(self, args: list[str]) -> tuple[int, bool]:
        """Parse statement command arguments for years and quarterly flag.

        Args:
            args: List of arguments after the symbol (e.g., ["5", "Q"] or ["4"])

        Returns:
            Tuple of (years/quarters, is_quarterly)
        """
        years = 4  # Default
        quarterly = False

        for arg in args:
            arg_upper = arg.upper()
            if arg_upper == "Q":
                quarterly = True
            elif arg.isdigit():
                years = int(arg)

        return years, quarterly

    @work(exclusive=True, group="income_statement")
    async def _show_income_statement(
        self, symbol: str, periods: int = 4, quarterly: bool = False
    ) -> None:
        """Show income statement for a symbol."""
        try:
            period_type = "quarterly" if quarterly else "annual"
            self._show_loading(f"Loading income statement for {symbol} ({periods} {period_type})...")

            import asyncio
            period_param = "quarter" if quarterly else "annual"
            quote, statements = await asyncio.gather(
                self._client.get_quote(symbol),
                self._financials_service.get_income_statement(
                    symbol, limit=periods, period=period_param
                ),
            )

            if not statements:
                self._show_content(f"[dim]No income statement data found for {symbol}.[/dim]")
                return

            currency = get_currency_symbol(quote.exchange)
            content = f"[bold cyan]Income Statement: {symbol.upper()} ({period_type.title()})[/bold cyan]\n"
            content += self._financials_service.format_income_statement_table(statements, currency)

            self._show_content(content)
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="balance_sheet")
    async def _show_balance_sheet(
        self, symbol: str, periods: int = 4, quarterly: bool = False
    ) -> None:
        """Show balance sheet for a symbol."""
        try:
            period_type = "quarterly" if quarterly else "annual"
            self._show_loading(f"Loading balance sheet for {symbol} ({periods} {period_type})...")

            import asyncio
            period_param = "quarter" if quarterly else "annual"
            quote, statements = await asyncio.gather(
                self._client.get_quote(symbol),
                self._financials_service.get_balance_sheet(
                    symbol, limit=periods, period=period_param
                ),
            )

            if not statements:
                self._show_content(f"[dim]No balance sheet data found for {symbol}.[/dim]")
                return

            currency = get_currency_symbol(quote.exchange)
            content = f"[bold cyan]Balance Sheet: {symbol.upper()} ({period_type.title()})[/bold cyan]\n"
            content += self._financials_service.format_balance_sheet_table(statements, currency)

            self._show_content(content)
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="cash_flow")
    async def _show_cash_flow(
        self, symbol: str, periods: int = 4, quarterly: bool = False
    ) -> None:
        """Show cash flow statement for a symbol."""
        try:
            period_type = "quarterly" if quarterly else "annual"
            self._show_loading(f"Loading cash flow statement for {symbol} ({periods} {period_type})...")

            import asyncio
            period_param = "quarter" if quarterly else "annual"
            quote, statements = await asyncio.gather(
                self._client.get_quote(symbol),
                self._financials_service.get_cash_flow_statement(
                    symbol, limit=periods, period=period_param
                ),
            )

            if not statements:
                self._show_content(f"[dim]No cash flow data found for {symbol}.[/dim]")
                return

            currency = get_currency_symbol(quote.exchange)
            content = f"[bold cyan]Cash Flow Statement: {symbol.upper()} ({period_type.title()})[/bold cyan]\n"
            content += self._financials_service.format_cash_flow_table(statements, currency)

            self._show_content(content)
        except SymbolNotFoundError as e:
            self._show_message(f"Symbol not found: {e.symbol}", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="news")
    async def _show_news(self, symbol: Optional[str] = None) -> None:
        """Show news articles."""
        try:
            label = f"news for {symbol}" if symbol else "market news"
            self._show_loading(f"Loading {label}...")

            if symbol:
                articles = await self._news_service.get_symbol_news(symbol, limit=10)
            else:
                articles = await self._news_service.get_market_news(limit=10)

            if not articles:
                self._show_content("[dim]No news articles found.[/dim]")
                return

            content = f"[bold cyan]{'Stock' if symbol else 'Market'} News[/bold cyan]\n"
            content += "=" * 50 + "\n\n"

            for article in articles:
                date_str = self._news_service.format_published_date(article)
                content += f"[bold white]{article.title}[/bold white]\n"
                content += f"[dim]{article.site} - {date_str}[/dim]\n"
                if article.text:
                    content += f"{self._news_service.truncate_text(article.text, 200)}\n"
                content += "\n"

            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="watchlist")
    async def _show_watchlist(self) -> None:
        """Show the watchlist."""
        try:
            self._show_loading("Loading watchlist...")
            quotes = await self._watchlist_service.get_watchlist_quotes("default")

            watchlist = self.query_one(WatchlistWidget)
            watchlist.update_quotes(quotes)
            watchlist.display = True

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#content-scroll").display = False
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="watchlist")
    async def _add_to_watchlist(self, symbol: str) -> None:
        """Add a symbol to the watchlist."""
        try:
            added = await self._watchlist_service.add_symbol(symbol.upper())
            if added:
                self._show_message(f"Added {symbol.upper()} to watchlist", error=False)
                self._load_ticker_data()  # Refresh ticker
            else:
                self._show_message(f"{symbol.upper()} is already in watchlist", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="watchlist")
    async def _remove_from_watchlist(self, symbol: str) -> None:
        """Remove a symbol from the watchlist."""
        try:
            removed = await self._watchlist_service.remove_symbol(symbol.upper())
            if removed:
                self._show_message(f"Removed {symbol.upper()} from watchlist", error=False)
                self._load_ticker_data()  # Refresh ticker
            else:
                self._show_message(f"{symbol.upper()} is not in watchlist", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="search")
    async def _search_symbols(self, query: str) -> None:
        """Search for symbols."""
        try:
            self._show_loading(f"Searching for '{query}'...")
            results = await self._search_service.search(query, limit=10)

            if not results:
                self._show_content(f"[dim]No results found for '{query}'[/dim]")
                return

            content = f"[bold cyan]Search Results: '{query}'[/bold cyan]\n"
            content += "=" * 50 + "\n\n"

            for result in results:
                content += f"[bold yellow]{result.symbol}[/bold yellow] - {result.name}\n"
                content += f"[dim]{result.exchange} | {result.currency}[/dim]\n\n"

            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_world_indices(self) -> None:
        """Show world equity indices."""
        try:
            self._show_loading("Loading world indices...")
            quotes = await self._dashboard_service.get_world_indices()
            content = self._dashboard_service.format_indices(quotes)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_top_news(self) -> None:
        """Show top news headlines."""
        try:
            self._show_loading("Loading top news...")
            articles = await self._news_service.get_market_news(limit=15)
            content = self._dashboard_service.format_news(articles)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_most_active(self) -> None:
        """Show most active stocks by volume."""
        try:
            self._show_loading("Loading most active stocks...")
            quotes = await self._dashboard_service.get_most_active(limit=20)
            content = self._dashboard_service.format_most_active(quotes)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_treasury_rates(self) -> None:
        """Show US Treasury yields."""
        try:
            self._show_loading("Loading treasury rates...")
            rates = await self._dashboard_service.get_treasury_rates()
            content = self._dashboard_service.format_treasury_rates(rates)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_forex(self) -> None:
        """Show foreign exchange rates."""
        try:
            self._show_loading("Loading forex rates...")
            rates = await self._dashboard_service.get_forex_rates()
            content = self._dashboard_service.format_forex(rates)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_economic_stats(self) -> None:
        """Show economic statistics from FRED."""
        try:
            self._show_loading("Loading economic statistics...")
            stats = await self._dashboard_service.get_economic_stats()
            content = self._dashboard_service.format_economic_stats(stats)
            self._show_content(content)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    def _show_content(self, content: str) -> None:
        """Show content in the content area."""
        self.query_one(QuotePanel).display = False
        self.query_one("#chart-widget").display = False
        self.query_one("#watchlist-widget").display = False

        content_area = self.query_one("#content-area", Static)
        content_area.update(content)
        self.query_one("#content-scroll").display = True

    def _show_loading(self, message: str) -> None:
        """Show loading message."""
        content_area = self.query_one("#content-area", Static)
        content_area.update(f"[italic dim]{message}[/italic dim]")

    def _show_message(self, message: str, error: bool = False) -> None:
        """Show a status message."""
        style = "red bold" if error else "green"
        self.notify(message, severity="error" if error else "information")

    def action_show_help(self) -> None:
        """Show help in content area."""
        self._show_content(self._get_help_text())

    def action_focus_command(self) -> None:
        """Focus the command bar."""
        self.query_one(CommandBar).focus_input()

    def action_show_watchlist(self) -> None:
        """Show watchlist shortcut."""
        self._show_watchlist()

    def _get_help_text(self) -> str:
        """Get help text content."""
        return """[bold cyan]Boomberg - Help[/bold cyan]

[bold yellow]Symbol Commands:[/bold yellow]
  Q <SYMBOL>      Get quote (e.g., Q AAPL)
  GP <SYMBOL>     Price chart (e.g., GP MSFT 1M)
                  Periods: 1D, 1W, 1M, 3M, 6M, 1Y, 5Y
  FA <SYMBOL>     Fundamentals (e.g., FA GOOGL)
  FI <SYMBOL>     Financials & ratios (e.g., FI AAPL)
  IS <SYMBOL> [N] [Q]  Income statement (e.g., IS AAPL 5)
  BS <SYMBOL> [N] [Q]  Balance sheet (e.g., BS AAPL 4)
  CF <SYMBOL> [N] [Q]  Cash flow (e.g., CF AAPL 8 Q)
                  N = years (default 4), Q = quarterly
  N [SYMBOL]      News (market news or symbol-specific)
  S <QUERY>       Search symbols

[bold yellow]Dashboard Commands:[/bold yellow]
  WEI             World Equity Indices
  TOP             Top News Headlines
  MOST            Most Active Stocks
  WB              World Bond / Treasury Yields
  FXIP            Foreign Exchange Rates
  ECST            Economic Statistics (requires FRED_API_KEY)

[bold yellow]Watchlist Commands:[/bold yellow]
  W               Show watchlist
  WA <SYMBOL>     Add to watchlist
  WD <SYMBOL>     Remove from watchlist

[bold yellow]Keyboard Shortcuts:[/bold yellow]
  ?               Toggle this help
  Escape          Focus command bar
  Ctrl+W          Show watchlist
  q               Quit

[dim]Press Escape to close[/dim]"""


def run() -> None:
    """Run the Boomberg app."""
    app = Boomberg()
    app.run()


if __name__ == "__main__":
    run()
