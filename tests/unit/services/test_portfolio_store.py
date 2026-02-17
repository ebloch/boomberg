"""Unit tests for portfolio store."""

import json
import pytest
from pathlib import Path

from boomberg.storage.portfolio_store import PortfolioStore


class TestPortfolioStore:
    """Tests for PortfolioStore."""

    @pytest.fixture
    def temp_path(self, tmp_path) -> Path:
        """Create a temporary file path."""
        return tmp_path / "portfolio.json"

    @pytest.fixture
    def store(self, temp_path) -> PortfolioStore:
        """Create a store with temp path."""
        return PortfolioStore(str(temp_path))

    def test_load_nonexistent_file(self, store):
        """Test loading when file doesn't exist returns empty portfolio."""
        result = store.load()
        assert result == {}

    def test_load_existing_file(self, temp_path, store):
        """Test loading existing portfolio data."""
        data = {
            "AAPL": {"shares": 100, "cost_basis": 150.00},
            "GOOGL": {"shares": 50, "cost_basis": 2800.00},
        }
        with open(temp_path, "w") as f:
            json.dump(data, f)

        result = store.load()
        assert result == data
        assert result["AAPL"]["shares"] == 100
        assert result["AAPL"]["cost_basis"] == 150.00

    def test_load_invalid_json(self, temp_path, store):
        """Test loading invalid JSON returns empty portfolio."""
        with open(temp_path, "w") as f:
            f.write("not valid json")

        result = store.load()
        assert result == {}

    def test_load_invalid_structure(self, temp_path, store):
        """Test loading invalid structure returns empty portfolio."""
        with open(temp_path, "w") as f:
            json.dump(["not", "a", "dict"], f)

        result = store.load()
        assert result == {}

    def test_save(self, temp_path, store):
        """Test saving portfolio data."""
        data = {
            "AAPL": {"shares": 100, "cost_basis": 150.00},
            "MSFT": {"shares": 75, "cost_basis": 380.00},
        }
        store.save(data)

        with open(temp_path, "r") as f:
            saved_data = json.load(f)

        assert saved_data == data

    def test_exists_true(self, temp_path, store):
        """Test exists returns True when file exists."""
        temp_path.write_text("{}")
        assert store.exists() is True

    def test_exists_false(self, store):
        """Test exists returns False when file doesn't exist."""
        assert store.exists() is False

    def test_default_path(self):
        """Test default path is set correctly."""
        store = PortfolioStore()
        assert "portfolio.json" in str(store._path)
