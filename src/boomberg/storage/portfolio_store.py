"""Portfolio persistence storage."""

import json
from pathlib import Path
from typing import Optional

from boomberg.config import get_default_data_dir


class PortfolioStore:
    """Persists portfolio holdings to JSON file."""

    def __init__(self, path: Optional[str] = None):
        if path is None:
            self._path = get_default_data_dir() / "portfolio.json"
        else:
            self._path = Path(path)

    def load(self) -> dict[str, dict]:
        """Load portfolio from file.

        Returns:
            Dict mapping symbol to holding info:
            {
                "AAPL": {"shares": 100, "cost_basis": 150.00},
                "GOOGL": {"shares": 50, "cost_basis": 2800.00},
            }
        """
        if not self._path.exists():
            return {}

        try:
            with open(self._path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {}
                return data
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, portfolio: dict[str, dict]) -> None:
        """Save portfolio to file."""
        with open(self._path, "w") as f:
            json.dump(portfolio, f, indent=2)

    def exists(self) -> bool:
        """Check if the storage file exists."""
        return self._path.exists()
