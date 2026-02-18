"""Portfolio service for tracking holdings and performance."""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.storage.portfolio_store import PortfolioStore


@dataclass
class PortfolioHolding:
    """Represents a portfolio holding with current market data."""

    symbol: str
    name: str
    shares: float
    cost_basis: float  # Per share cost
    current_price: float
    total_value: float  # shares * current_price
    total_cost: float  # shares * cost_basis
    gain_loss: float  # total_value - total_cost
    gain_loss_percent: float  # (gain_loss / total_cost) * 100
    change_1d_value: float  # Today's change in $
    change_1d_pct: float  # Today's change in %
    change_mtd_value: float  # Month-to-date change in $
    change_mtd_pct: float  # Month-to-date change in %
    change_ytd_value: float  # Year-to-date change in $
    change_ytd_pct: float  # Year-to-date change in %
    exchange: str = ""


class PortfolioService:
    """Service for managing portfolio holdings and calculating performance."""

    def __init__(self, store: PortfolioStore, client: FMPClient):
        self._store = store
        self._client = client

    def get_holdings(self) -> dict[str, dict]:
        """Get raw holdings data from store."""
        return self._store.load()

    def add_holding(self, symbol: str, shares: float, total_cost: float) -> None:
        """Add or update a holding.

        If the symbol already exists, adds shares and combines total cost.
        """
        symbol = symbol.upper()
        holdings = self._store.load()

        if symbol in holdings:
            # Add to existing position
            existing = holdings[symbol]
            new_shares = existing["shares"] + shares
            new_total_cost = existing["total_cost"] + total_cost

            holdings[symbol] = {
                "shares": new_shares,
                "total_cost": new_total_cost,
            }
        else:
            holdings[symbol] = {
                "shares": shares,
                "total_cost": total_cost,
            }

        self._store.save(holdings)

    def remove_holding(self, symbol: str) -> None:
        """Remove a holding completely."""
        symbol = symbol.upper()
        holdings = self._store.load()

        if symbol not in holdings:
            raise KeyError(f"Symbol {symbol} not found in portfolio")

        del holdings[symbol]
        self._store.save(holdings)

    def update_shares(self, symbol: str, shares: float) -> None:
        """Update the share count for an existing holding."""
        symbol = symbol.upper()
        holdings = self._store.load()

        if symbol not in holdings:
            raise KeyError(f"Symbol {symbol} not found in portfolio")

        holdings[symbol]["shares"] = shares
        self._store.save(holdings)

    async def get_portfolio_with_quotes(self) -> list[PortfolioHolding]:
        """Get portfolio holdings with current quotes and performance metrics."""
        holdings = self._store.load()

        if not holdings:
            return []

        symbols = list(holdings.keys())

        # Fetch current quotes and price changes in parallel
        quotes = await self._client.get_quotes(symbols)
        quote_map = {q.symbol: q for q in quotes}

        # Fetch precalculated price changes from FMP (includes YTD)
        price_changes = await self._client.get_stock_price_changes(symbols)
        price_change_map = {pc.symbol: pc for pc in price_changes}

        # Calculate MTD dates (still need historical for MTD)
        today = date.today()
        mtd_start = today.replace(day=1)

        result = []
        for symbol, data in holdings.items():
            quote = quote_map.get(symbol)
            if not quote:
                continue

            shares = data["shares"]
            total_cost = data["total_cost"]
            current_price = quote.price
            total_value = shares * current_price
            cost_basis = total_cost / shares if shares > 0 else 0  # Per-share cost for display
            gain_loss = total_value - total_cost
            gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0

            # Daily change from quote
            change_1d_value = shares * quote.change
            change_1d_pct = quote.change_percent

            # Get YTD from FMP's precalculated values
            change_ytd_pct = 0.0
            change_ytd_value = 0.0
            price_change = price_change_map.get(symbol)
            if price_change and price_change.ytd is not None:
                change_ytd_pct = price_change.ytd
                # Calculate YTD value: derive start price from current price and YTD %
                # start_price = current_price / (1 + ytd_pct/100)
                # ytd_value = shares * (current_price - start_price)
                if change_ytd_pct != -100:  # Avoid division by zero
                    ytd_start_price = current_price / (1 + change_ytd_pct / 100)
                    change_ytd_value = shares * (current_price - ytd_start_price)

            # Try to get MTD changes from historical data
            change_mtd_value = 0.0
            change_mtd_pct = 0.0

            try:
                # Fetch historical prices for MTD calculation only
                historical = await self._client.get_historical_prices(
                    symbol, from_date=mtd_start, to_date=today
                )
                if historical:
                    # Sort by date ascending
                    historical = sorted(historical, key=lambda x: x.date)

                    # Find MTD start price (first trading day of month)
                    mtd_start_price = historical[0].close if historical else current_price

                    # Calculate MTD
                    if mtd_start_price > 0:
                        change_mtd_pct = ((current_price - mtd_start_price) / mtd_start_price) * 100
                        change_mtd_value = shares * (current_price - mtd_start_price)

            except Exception:
                # If historical data fails, leave as 0
                pass

            holding = PortfolioHolding(
                symbol=symbol,
                name=quote.name,
                shares=shares,
                cost_basis=cost_basis,
                current_price=current_price,
                total_value=total_value,
                total_cost=total_cost,
                gain_loss=gain_loss,
                gain_loss_percent=gain_loss_percent,
                change_1d_value=change_1d_value,
                change_1d_pct=change_1d_pct,
                change_mtd_value=change_mtd_value,
                change_mtd_pct=change_mtd_pct,
                change_ytd_value=change_ytd_value,
                change_ytd_pct=change_ytd_pct,
                exchange=quote.exchange,
            )
            result.append(holding)

        return result

    @staticmethod
    def format_currency(value: float) -> str:
        """Format value as currency."""
        if value < 0:
            return f"-${abs(value):,.2f}"
        return f"${value:,.2f}"

    @staticmethod
    def format_percent(value: float) -> str:
        """Format value as percentage with sign."""
        sign = "+" if value >= 0 else ""
        return f"{sign}{value:.2f}%"
