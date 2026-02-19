"""Main Boomberg application."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import on, work
from textual.app import App, ComposeResult, SystemCommand
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Static

from boomberg.api.client import FMPClient
from boomberg.api.eodhd_client import EODHDClient
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
from boomberg.services.portfolio import PortfolioService
from boomberg.storage.watchlist_store import WatchlistStore
from boomberg.storage.portfolio_store import PortfolioStore
from boomberg.ui.widgets.chart import ChartWidget
from boomberg.ui.widgets.command_bar import CommandBar
from boomberg.ui.widgets.quote_panel import QuotePanel, get_currency_symbol
from boomberg.ui.widgets.ticker_tape import TickerTape
from boomberg.ui.widgets.watchlist import WatchlistWidget
from boomberg.ui.widgets.portfolio import PortfolioWidget
from boomberg.ui.widgets.snapshot import SnapshotWidget
from boomberg.ui.widgets.bonds import BondsWidget


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
        self._eodhd_client: Optional[EODHDClient] = None
        self._quote_service: Optional[QuoteService] = None
        self._watchlist_service: Optional[WatchlistService] = None
        self._historical_service: Optional[HistoricalService] = None
        self._fundamentals_service: Optional[FundamentalsService] = None
        self._financials_service: Optional[FinancialsService] = None
        self._news_service: Optional[NewsService] = None
        self._search_service: Optional[SearchService] = None
        self._dashboard_service: Optional[DashboardService] = None
        self._portfolio_service: Optional[PortfolioService] = None
        self._current_symbol: Optional[str] = None
        self._current_screen: Optional[str] = None
        self._current_screen_args: tuple = ()

    def compose(self) -> ComposeResult:
        yield Header()
        yield TickerTape(id="ticker-tape")
        yield Container(
            Vertical(
                QuotePanel(id="quote-panel"),
                ChartWidget(id="chart-widget"),
                WatchlistWidget(id="watchlist-widget"),
                PortfolioWidget(id="portfolio-widget"),
                SnapshotWidget(id="snapshot-widget"),
                BondsWidget(id="bonds-widget"),
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

        # Initialize EODHD client if API key is configured
        if self._settings.eodhd_api_key:
            self._eodhd_client = EODHDClient(self._settings)
            await self._eodhd_client.__aenter__()

        store = WatchlistStore(self._settings.watchlist_path)
        self._quote_service = QuoteService(self._client)
        self._watchlist_service = WatchlistService(self._client, store)
        self._historical_service = HistoricalService(self._client)
        self._fundamentals_service = FundamentalsService(self._client)
        self._financials_service = FinancialsService(self._client)
        self._news_service = NewsService(self._client)
        self._search_service = SearchService(self._client)
        self._dashboard_service = DashboardService(
            self._client, self._fred_client, self._eodhd_client
        )

        portfolio_store = PortfolioStore()
        self._portfolio_service = PortfolioService(portfolio_store, self._client)

        # Focus command bar
        self.query_one(CommandBar).focus_input()

        # Load initial watchlist for ticker
        self._load_ticker_data()

        # Auto-refresh ticker every 5 minutes
        self.set_interval(300, self._load_ticker_data)

        # Auto-refresh current screen every 15 minutes
        self.set_interval(900, self._refresh_current_screen)

        # Hide widgets initially
        self.query_one("#chart-widget").display = False
        self.query_one("#watchlist-widget").display = False
        self.query_one("#portfolio-widget").display = False
        self.query_one("#snapshot-widget").display = False
        self.query_one("#bonds-widget").display = False
        self.query_one("#content-scroll").display = False

        # Show market snapshot on startup
        self._show_market_snapshot()

    async def on_unmount(self) -> None:
        """Clean up when app unmounts."""
        if self._eodhd_client:
            await self._eodhd_client.__aexit__(None, None, None)
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
            if args:
                self._show_country_bonds(args[0])
            else:
                self._show_international_bonds()
        elif command == "FXIP":
            self._show_forex()
        elif command == "ECST":
            self._show_economic_stats()
        elif command == "SNAP":
            self._show_market_snapshot()
        elif command == "P":
            self._show_portfolio()
        elif command == "PA" and len(args) >= 3:
            # PA <symbol> <shares> <total_cost>
            try:
                shares = float(args[1])
                total_cost = float(args[2])
                self._add_to_portfolio(args[0], shares, total_cost)
            except ValueError:
                self._show_message("Invalid format. Use: PA <SYMBOL> <SHARES> <TOTAL_COST>", error=True)
        elif command == "PR" and args:
            self._remove_from_portfolio(args[0])
        elif command == "PU" and len(args) >= 2:
            # PU <symbol> <shares>
            try:
                shares = float(args[1])
                self._update_portfolio_shares(args[0], shares)
            except ValueError:
                self._show_message("Invalid format. Use: PU <SYMBOL> <SHARES>", error=True)
        elif command in ("?", "HELP"):
            self.action_show_help()
        else:
            self._show_message(f"Unknown command: {command}. Press ? for help.", error=True)

    @work(exclusive=True, group="quote")
    async def _show_quote(self, symbol: str) -> None:
        """Show quote for a symbol."""
        import asyncio
        from boomberg.ui.widgets.quote_panel import PriceChanges

        try:
            self._show_loading(f"Loading quote for {symbol}...")

            # Fetch quote, price changes, and news in parallel
            quote, changes_result, news_result = await asyncio.gather(
                self._quote_service.get_quote(symbol),
                self._client.get_stock_price_changes([symbol.upper()]),
                self._news_service.get_symbol_news(symbol, limit=3),
                return_exceptions=True,
            )

            # Handle quote result (raise if exception)
            if isinstance(quote, Exception):
                raise quote

            self._current_symbol = symbol.upper()

            # Process price changes result
            price_changes = None
            if not isinstance(changes_result, Exception) and changes_result:
                pc = changes_result[0]
                price_changes = PriceChanges(
                    change_3m=pc.three_month or 0.0,
                    change_ytd=pc.ytd or 0.0,
                    change_5y=pc.five_year or 0.0,
                    change_10y=pc.ten_year or 0.0,
                )

            # Process news result
            news = None
            if not isinstance(news_result, Exception):
                news = news_result

            quote_panel = self.query_one(QuotePanel)
            quote_panel.update_quote(quote, price_changes, news=news)
            quote_panel.display = True

            self._current_screen = "quote"
            self._current_screen_args = (symbol,)

            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#bonds-widget").display = False
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

            self._current_screen = "chart"
            self._current_screen_args = (symbol, period)

            self.query_one(QuotePanel).display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#bonds-widget").display = False
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

            from rich.text import Text as RichText
            from rich.console import Group

            parts = []
            parts.append(RichText(f"{'Stock' if symbol else 'Market'} News", style="bold cyan"))
            parts.append(RichText("=" * 50))
            parts.append(RichText(""))

            for article in articles:
                date_str = self._news_service.format_published_date(article)

                # Title
                parts.append(RichText(article.title, style="bold white"))

                # Source (clickable) and date
                if article.url:
                    source_text = RichText(article.site, style="dim")
                    source_text.stylize(f"link {article.url}")
                    meta_text = RichText()
                    meta_text.append_text(source_text)
                    meta_text.append(f" - {date_str}", style="dim")
                    parts.append(meta_text)
                else:
                    parts.append(RichText(f"{article.site} - {date_str}", style="dim"))

                # Text snippet
                if article.text:
                    parts.append(RichText(self._news_service.truncate_text(article.text, 200)))

                parts.append(RichText(""))  # Spacing

            self._show_rich_content(Group(*parts))
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="watchlist")
    async def _show_watchlist(self) -> None:
        """Show the watchlist."""
        try:
            self._show_loading("Loading watchlist...")
            quotes = await self._watchlist_service.get_watchlist_with_changes("default")

            watchlist = self.query_one(WatchlistWidget)
            watchlist.update_quotes(quotes)
            watchlist.display = True

            self._current_screen = "watchlist"
            self._current_screen_args = ()

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#bonds-widget").display = False
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
                await self._refresh_watchlist_if_visible()
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
                await self._refresh_watchlist_if_visible()
            else:
                self._show_message(f"{symbol.upper()} is not in watchlist", error=True)
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    async def _refresh_watchlist_if_visible(self) -> None:
        """Refresh watchlist view if it's currently visible."""
        watchlist_widget = self.query_one(WatchlistWidget)
        if watchlist_widget.display:
            quotes = await self._watchlist_service.get_watchlist_with_changes("default")
            watchlist_widget.update_quotes(quotes)

    @work(exclusive=True, group="portfolio")
    async def _show_portfolio(self) -> None:
        """Show the portfolio."""
        try:
            self._show_loading("Loading portfolio...")
            holdings = await self._portfolio_service.get_portfolio_with_quotes()

            portfolio_widget = self.query_one(PortfolioWidget)
            portfolio_widget.update_holdings(holdings)
            portfolio_widget.display = True

            self._current_screen = "portfolio"
            self._current_screen_args = ()

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#bonds-widget").display = False
            self.query_one("#content-scroll").display = False
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="portfolio")
    async def _add_to_portfolio(self, symbol: str, shares: float, total_cost: float) -> None:
        """Add a holding to the portfolio."""
        try:
            self._portfolio_service.add_holding(symbol.upper(), shares, total_cost)
            self._show_message(f"Added {shares:.0f} shares of {symbol.upper()} (total cost: ${total_cost:,.2f})", error=False)
            await self._refresh_portfolio_if_visible()
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="portfolio")
    async def _remove_from_portfolio(self, symbol: str) -> None:
        """Remove a holding from the portfolio."""
        try:
            self._portfolio_service.remove_holding(symbol.upper())
            self._show_message(f"Removed {symbol.upper()} from portfolio", error=False)
            await self._refresh_portfolio_if_visible()
        except KeyError:
            self._show_message(f"{symbol.upper()} is not in portfolio", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="portfolio")
    async def _update_portfolio_shares(self, symbol: str, shares: float) -> None:
        """Update share count for a holding."""
        try:
            self._portfolio_service.update_shares(symbol.upper(), shares)
            self._show_message(f"Updated {symbol.upper()} to {shares:.0f} shares", error=False)
            await self._refresh_portfolio_if_visible()
        except KeyError:
            self._show_message(f"{symbol.upper()} is not in portfolio", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    async def _refresh_portfolio_if_visible(self) -> None:
        """Refresh portfolio view if it's currently visible."""
        portfolio_widget = self.query_one(PortfolioWidget)
        if portfolio_widget.display:
            holdings = await self._portfolio_service.get_portfolio_with_quotes()
            portfolio_widget.update_holdings(holdings)

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
            self._current_screen = "wei"
            self._current_screen_args = ()
            self._show_content(content, title="World Equity Indices")
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

            if not articles:
                self._show_content("[dim]No news available.[/dim]")
                return

            from rich.text import Text as RichText
            from rich.console import Group

            parts = []
            for article in articles:
                # Title
                parts.append(RichText(article.title, style="bold white"))

                # Source (clickable) and date
                date_str = self._news_service.format_published_date(article)
                if article.site:
                    source_text = RichText(article.site, style="dim")
                    if article.url:
                        source_text.stylize(f"link {article.url}")
                    meta_text = RichText()
                    meta_text.append_text(source_text)
                    meta_text.append(f" - {date_str}", style="dim")
                    parts.append(meta_text)
                else:
                    parts.append(RichText(date_str, style="dim"))

                parts.append(RichText(""))

            self._show_rich_content(Group(*parts), title="Top News Headlines")
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
    async def _show_international_bonds(self) -> None:
        """Show international government bond yields snapshot."""
        try:
            self._show_loading("Loading international bond yields...")
            snapshot = await self._dashboard_service.get_international_bond_snapshot()

            bonds_widget = self.query_one(BondsWidget)
            bonds_widget.update_snapshot(snapshot)
            bonds_widget.display = True

            self._current_screen = "bonds"
            self._current_screen_args = ()

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#content-scroll").display = False
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    @work(exclusive=True, group="dashboard")
    async def _show_country_bonds(self, country_code: str) -> None:
        """Show government bond yields for a specific country."""
        try:
            self._show_loading(f"Loading bond yields for {country_code.upper()}...")
            detail = await self._dashboard_service.get_country_bond_detail(country_code)
            if detail is None:
                self._show_message(
                    f"Unknown country code: {country_code.upper()}. "
                    "Use: US, CA, DE, UK, JP, FR, AU, IT, ES, CN",
                    error=True,
                )
                return

            bonds_widget = self.query_one(BondsWidget)
            bonds_widget.update_detail(detail)
            bonds_widget.display = True

            self._current_screen = "bonds_detail"
            self._current_screen_args = (country_code,)

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#snapshot-widget").display = False
            self.query_one("#content-scroll").display = False
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
            self._current_screen = "forex"
            self._current_screen_args = ()
            self._show_content(content, title="Currency ETFs")
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

    @work(exclusive=True, group="dashboard")
    async def _show_market_snapshot(self) -> None:
        """Show consolidated market snapshot."""
        try:
            self._show_loading("Loading market snapshot...")
            snapshot = await self._dashboard_service.get_market_snapshot()

            snapshot_widget = self.query_one(SnapshotWidget)
            snapshot_widget.update_snapshot(
                indices=snapshot.get("indices", []),
                commodities=snapshot.get("commodities", []),
                sectors=snapshot.get("sectors", []),
                bonds=snapshot.get("bonds", {}),
            )
            snapshot_widget.display = True

            self._current_screen = "snapshot"
            self._current_screen_args = ()

            self.query_one(QuotePanel).display = False
            self.query_one("#chart-widget").display = False
            self.query_one("#watchlist-widget").display = False
            self.query_one("#portfolio-widget").display = False
            self.query_one("#bonds-widget").display = False
            self.query_one("#content-scroll").display = False
        except APIError as e:
            self._show_message(f"API error: {e.message}", error=True)
        except Exception as e:
            self._show_message(f"Error: {str(e)}", error=True)

    def _refresh_current_screen(self) -> None:
        """Refresh the currently displayed screen."""
        if not self._current_screen:
            return

        if self._current_screen == "quote":
            self._show_quote(self._current_screen_args[0])
        elif self._current_screen == "chart":
            self._show_chart(*self._current_screen_args)
        elif self._current_screen == "watchlist":
            self._show_watchlist()
        elif self._current_screen == "portfolio":
            self._show_portfolio()
        elif self._current_screen == "snapshot":
            self._show_market_snapshot()
        elif self._current_screen == "wei":
            self._show_world_indices()
        elif self._current_screen == "forex":
            self._show_forex()
        elif self._current_screen == "bonds":
            self._show_international_bonds()
        elif self._current_screen == "bonds_detail":
            self._show_country_bonds(self._current_screen_args[0])
        # Skip "content" screens (static text like help, fundamentals)

    def _show_content(self, content: str, title: str = "") -> None:
        """Show content in the content area."""
        self.query_one(QuotePanel).display = False
        self.query_one("#chart-widget").display = False
        self.query_one("#watchlist-widget").display = False
        self.query_one("#portfolio-widget").display = False
        self.query_one("#snapshot-widget").display = False
        self.query_one("#bonds-widget").display = False

        # Only set to "content" if not already set by a refreshable screen
        # (wei, forex set their screen before calling this)
        if self._current_screen not in ("wei", "forex"):
            self._current_screen = "content"
            self._current_screen_args = ()

        content_area = self.query_one("#content-area", Static)
        content_area.update(content)
        content_scroll = self.query_one("#content-scroll")
        content_scroll.border_title = title
        content_scroll.display = True

    def _show_rich_content(self, content, title: str = "") -> None:
        """Show rich renderable content in the content area."""
        self.query_one(QuotePanel).display = False
        self.query_one("#chart-widget").display = False
        self.query_one("#watchlist-widget").display = False
        self.query_one("#portfolio-widget").display = False
        self.query_one("#snapshot-widget").display = False
        self.query_one("#bonds-widget").display = False

        self._current_screen = "content"
        self._current_screen_args = ()

        content_area = self.query_one("#content-area", Static)
        content_area.update(content)
        content_scroll = self.query_one("#content-scroll")
        content_scroll.border_title = title
        content_scroll.display = True

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
  SNAP            Market Snapshot (indices, commodities, sectors, bonds)
  WEI             World Equity Indices
  TOP             Top News Headlines
  MOST            Most Active Stocks
  WB              International Bond Yields (snapshot)
  WB <CODE>       Country bond detail (US, CA, DE, UK, JP, FR, AU, IT, ES, CN)
  FXIP            Foreign Exchange Rates
  ECST            Economic Statistics (requires FRED_API_KEY)

[bold yellow]Watchlist Commands:[/bold yellow]
  W               Show watchlist
  WA <SYMBOL>     Add to watchlist
  WD <SYMBOL>     Remove from watchlist

[bold yellow]Portfolio Commands:[/bold yellow]
  P               Show portfolio
  PA <SYM> <SHARES> <TOTAL_COST>  Add holding (e.g., PA AAPL 100 15000)
  PR <SYMBOL>     Remove holding from portfolio
  PU <SYM> <SHARES>  Update share count (e.g., PU AAPL 150)

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
