"""Unit tests for WatchlistStore."""

import json
import tempfile
from pathlib import Path

import pytest

from boomberg.storage.watchlist_store import WatchlistStore


class TestWatchlistStore:
    """Tests for WatchlistStore."""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            yield f.name
        Path(f.name).unlink(missing_ok=True)

    def test_load_nonexistent_file(self, temp_file):
        """Test loading from non-existent file returns default."""
        Path(temp_file).unlink(missing_ok=True)
        store = WatchlistStore(temp_file)

        result = store.load()

        assert result == {"default": []}

    def test_load_existing_file(self, temp_file):
        """Test loading from existing file."""
        data = {"default": ["AAPL", "MSFT"], "tech": ["GOOGL", "AMZN"]}
        with open(temp_file, "w") as f:
            json.dump(data, f)

        store = WatchlistStore(temp_file)
        result = store.load()

        assert result == data

    def test_load_invalid_json(self, temp_file):
        """Test loading invalid JSON returns default."""
        with open(temp_file, "w") as f:
            f.write("not valid json")

        store = WatchlistStore(temp_file)
        result = store.load()

        assert result == {"default": []}

    def test_load_invalid_structure(self, temp_file):
        """Test loading non-dict JSON returns default."""
        with open(temp_file, "w") as f:
            json.dump(["AAPL", "MSFT"], f)

        store = WatchlistStore(temp_file)
        result = store.load()

        assert result == {"default": []}

    def test_save(self, temp_file):
        """Test saving watchlists."""
        store = WatchlistStore(temp_file)
        data = {"default": ["AAPL", "MSFT"], "tech": ["GOOGL"]}

        store.save(data)

        with open(temp_file, "r") as f:
            saved = json.load(f)
        assert saved == data

    def test_exists_true(self, temp_file):
        """Test exists returns True for existing file."""
        store = WatchlistStore(temp_file)
        store.save({"default": []})

        assert store.exists() is True

    def test_exists_false(self, temp_file):
        """Test exists returns False for non-existent file."""
        Path(temp_file).unlink(missing_ok=True)
        store = WatchlistStore(temp_file)

        assert store.exists() is False

    def test_default_path(self):
        """Test default path is watchlists.json."""
        store = WatchlistStore()
        assert store._path == Path("watchlists.json")
