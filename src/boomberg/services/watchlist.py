"""Watchlist service for managing user watchlists."""

from typing import Optional

from boomberg.api.client import FMPClient
from boomberg.api.models import Quote
from boomberg.storage.watchlist_store import WatchlistStore


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

    async def symbol_exists(self, symbol: str, watchlist: str = "default") -> bool:
        """Check if a symbol exists in a watchlist."""
        await self._ensure_loaded()
        return symbol.upper() in self._watchlists.get(watchlist, [])
