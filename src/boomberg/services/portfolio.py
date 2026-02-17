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

    def add_holding(self, symbol: str, shares: float, cost_basis: float) -> None:
        """Add or update a holding.

        If the symbol already exists, calculates new average cost basis.
        """
        symbol = symbol.upper()
        holdings = self._store.load()

        if symbol in holdings:
            # Calculate weighted average cost basis
            existing = holdings[symbol]
            total_shares = existing["shares"] + shares
            total_cost = (existing["shares"] * existing["cost_basis"]) + (shares * cost_basis)
            new_cost_basis = total_cost / total_shares

            holdings[symbol] = {
                "shares": total_shares,
                "cost_basis": new_cost_basis,
            }
        else:
            holdings[symbol] = {
                "shares": shares,
                "cost_basis": cost_basis,
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

        # Fetch current quotes
        quotes = await self._client.get_quotes(symbols)
        quote_map = {q.symbol: q for q in quotes}

        # Calculate MTD and YTD dates
        today = date.today()
        mtd_start = today.replace(day=1)
        ytd_start = today.replace(month=1, day=1)

        result = []
        for symbol, data in holdings.items():
            quote = quote_map.get(symbol)
            if not quote:
                continue

            shares = data["shares"]
            cost_basis = data["cost_basis"]
            current_price = quote.price
            total_value = shares * current_price
            total_cost = shares * cost_basis
            gain_loss = total_value - total_cost
            gain_loss_percent = (gain_loss / total_cost * 100) if total_cost > 0 else 0

            # Daily change from quote
            change_1d_value = shares * quote.change
            change_1d_pct = quote.change_percent

            # Try to get MTD and YTD changes from historical data
            change_mtd_value = 0.0
            change_mtd_pct = 0.0
            change_ytd_value = 0.0
            change_ytd_pct = 0.0

            try:
                # Fetch historical prices for MTD/YTD calculation
                historical = await self._client.get_historical_prices(
                    symbol, from_date=ytd_start, to_date=today
                )
                if historical:
                    # Sort by date ascending
                    historical = sorted(historical, key=lambda x: x.date)

                    # Find YTD start price (first trading day of year)
                    ytd_start_price = historical[0].close if historical else current_price

                    # Find MTD start price (first trading day of month)
                    mtd_prices = [h for h in historical if h.date >= mtd_start]
                    mtd_start_price = mtd_prices[0].close if mtd_prices else current_price

                    # Calculate MTD
                    if mtd_start_price > 0:
                        change_mtd_pct = ((current_price - mtd_start_price) / mtd_start_price) * 100
                        change_mtd_value = shares * (current_price - mtd_start_price)

                    # Calculate YTD
                    if ytd_start_price > 0:
                        change_ytd_pct = ((current_price - ytd_start_price) / ytd_start_price) * 100
                        change_ytd_value = shares * (current_price - ytd_start_price)

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
