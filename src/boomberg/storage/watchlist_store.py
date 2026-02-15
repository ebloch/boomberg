"""Watchlist persistence storage."""

import json
from pathlib import Path
from typing import Optional


class WatchlistStore:
    """Persists watchlists to JSON file."""

    def __init__(self, path: Optional[str] = None):
        self._path = Path(path or "watchlists.json")

    def load(self) -> dict[str, list[str]]:
        """Load watchlists from file."""
        if not self._path.exists():
            return {"default": []}

        try:
            with open(self._path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"default": []}
                return data
        except (json.JSONDecodeError, IOError):
            return {"default": []}

    def save(self, watchlists: dict[str, list[str]]) -> None:
        """Save watchlists to file."""
        with open(self._path, "w") as f:
            json.dump(watchlists, f, indent=2)

    def exists(self) -> bool:
        """Check if the storage file exists."""
        return self._path.exists()
