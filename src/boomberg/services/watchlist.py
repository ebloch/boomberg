"""Watchlist service for managing user watchlists."""

from dataclasses import dataclass
from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import Quote
from boomberg.storage.watchlist_store import WatchlistStore


@dataclass
class WatchlistQuote:
    """Quote with price change data for watchlist display."""

    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    volume: int
    exchange: str
    market_cap: Optional[float] = None
    pe: Optional[float] = None
    # Price changes from FMP
    change_1d: float = 0.0
    change_1m: float = 0.0
    change_ytd: float = 0.0
    change_3y: float = 0.0


class WatchlistService:
    """Service for managing watchlists."""

    def __init__(self, client: FMPClient, store: Optional[WatchlistStore] = None):
        self._client = client
        self._store = store or WatchlistStore()
        self._watchlists: dict[str, list[str]] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Ensure watchlists are loaded from storage."""
        if not self._loaded:
            self._watchlists = self._store.load()
            self._loaded = True

    async def get_watchlists(self) -> dict[str, list[str]]:
        """Get all watchlists."""
        await self._ensure_loaded()
        return self._watchlists.copy()

    async def get_watchlist(self, name: str = "default") -> list[str]:
        """Get symbols in a specific watchlist."""
        await self._ensure_loaded()
        return self._watchlists.get(name, []).copy()

    async def create_watchlist(self, name: str) -> None:
        """Create a new watchlist."""
        await self._ensure_loaded()
        if name not in self._watchlists:
            self._watchlists[name] = []
            self._store.save(self._watchlists)

    async def delete_watchlist(self, name: str) -> bool:
        """Delete a watchlist. Returns True if deleted, False if not found."""
        await self._ensure_loaded()
        if name in self._watchlists:
            del self._watchlists[name]
            self._store.save(self._watchlists)
            return True
        return False

    async def add_symbol(self, symbol: str, watchlist: str = "default") -> bool:
        """Add a symbol to a watchlist. Returns True if added, False if already exists."""
        await self._ensure_loaded()
        symbol = symbol.upper()

        if watchlist not in self._watchlists:
            self._watchlists[watchlist] = []

        if symbol not in self._watchlists[watchlist]:
            self._watchlists[watchlist].append(symbol)
            self._store.save(self._watchlists)
            return True
        return False

    async def remove_symbol(self, symbol: str, watchlist: str = "default") -> bool:
        """Remove a symbol from a watchlist. Returns True if removed, False if not found."""
        await self._ensure_loaded()
        symbol = symbol.upper()

        if watchlist in self._watchlists and symbol in self._watchlists[watchlist]:
            self._watchlists[watchlist].remove(symbol)
            self._store.save(self._watchlists)
            return True
        return False

    async def get_watchlist_quotes(self, watchlist: str = "default") -> list[Quote]:
        """Get quotes for all symbols in a watchlist."""
        symbols = await self.get_watchlist(watchlist)
        if not symbols:
            return []
        return await self._client.get_quotes(symbols)

    async def get_watchlist_with_changes(self, watchlist: str = "default") -> list[WatchlistQuote]:
        """Get watchlist quotes with price change data from FMP."""
        symbols = await self.get_watchlist(watchlist)
        if not symbols:
            return []

        # Fetch quotes and price changes
        quotes = await self._client.get_quotes(symbols)
        price_changes = await self._client.get_stock_price_changes(symbols)

        # Fetch PE ratios from ratios-ttm endpoint
        pe_map = await self._fetch_pe_ratios(symbols)

        # Build lookup for price changes
        change_map = {pc.symbol: pc for pc in price_changes}

        result = []
        for quote in quotes:
            pc = change_map.get(quote.symbol)
            pe = pe_map.get(quote.symbol)
            result.append(WatchlistQuote(
                symbol=quote.symbol,
                name=quote.name,
                price=quote.price,
                change=quote.change,
                change_percent=quote.change_percent,
                volume=quote.volume,
                exchange=quote.exchange,
                market_cap=quote.market_cap,
                pe=pe,
                change_1d=pc.one_day if pc and pc.one_day is not None else 0.0,
                change_1m=pc.one_month if pc and pc.one_month is not None else 0.0,
                change_ytd=pc.ytd if pc and pc.ytd is not None else 0.0,
                change_3y=pc.three_year if pc and pc.three_year is not None else 0.0,
            ))

        return result

    async def _fetch_pe_ratios(self, symbols: list[str]) -> dict[str, float]:
        """Fetch PE ratios for symbols from ratios-ttm endpoint."""
        import asyncio

        async def fetch_pe(symbol: str) -> tuple[str, float | None]:
            try:
                ratios = await self._client.get_financial_ratios_ttm(symbol)
                return (symbol, ratios.pe_ratio)
            except Exception:
                return (symbol, None)

        results = await asyncio.gather(*[fetch_pe(s) for s in symbols])
        return {symbol: pe for symbol, pe in results if pe is not None}

    async def symbol_exists(self, symbol: str, watchlist: str = "default") -> bool:
        """Check if a symbol exists in a watchlist."""
        await self._ensure_loaded()
        return symbol.upper() in self._watchlists.get(watchlist, [])
