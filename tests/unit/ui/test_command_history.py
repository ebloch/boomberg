"""Unit tests for command history."""

import pytest

from boomberg.ui.command_history import CommandHistory


class TestCommandHistory:
    """Tests for CommandHistory."""

    def test_empty_history_returns_empty_string_on_previous(self):
        """Test that navigating up in empty history returns empty string."""
        history = CommandHistory(max_size=10)
        assert history.previous() == ""

    def test_empty_history_returns_empty_string_on_next(self):
        """Test that navigating down in empty history returns empty string."""
        history = CommandHistory(max_size=10)
        assert history.next() == ""

    def test_add_command_and_retrieve_with_previous(self):
        """Test adding a command and retrieving it with previous()."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        assert history.previous() == "Q AAPL"

    def test_multiple_commands_navigate_backwards(self):
        """Test navigating backwards through multiple commands."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q MSFT")
        history.add("W")

        assert history.previous() == "W"
        assert history.previous() == "Q MSFT"
        assert history.previous() == "Q AAPL"

    def test_previous_at_beginning_stays_at_oldest(self):
        """Test that going past the oldest command stays at oldest."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q MSFT")

        assert history.previous() == "Q MSFT"
        assert history.previous() == "Q AAPL"
        assert history.previous() == "Q AAPL"  # Stays at oldest

    def test_next_navigates_forward(self):
        """Test navigating forward after going back."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q MSFT")
        history.add("W")

        history.previous()  # W
        history.previous()  # Q MSFT
        history.previous()  # Q AAPL

        assert history.next() == "Q MSFT"
        assert history.next() == "W"

    def test_next_at_end_returns_empty_string(self):
        """Test that going past the newest command returns empty string."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")

        history.previous()  # Q AAPL
        assert history.next() == ""  # Back to empty input
        assert history.next() == ""  # Stays at empty

    def test_max_size_drops_oldest_commands(self):
        """Test that history respects max_size by dropping oldest."""
        history = CommandHistory(max_size=3)
        history.add("cmd1")
        history.add("cmd2")
        history.add("cmd3")
        history.add("cmd4")  # Should drop cmd1

        assert history.previous() == "cmd4"
        assert history.previous() == "cmd3"
        assert history.previous() == "cmd2"
        assert history.previous() == "cmd2"  # No cmd1, stays at oldest

    def test_reset_position_after_add(self):
        """Test that adding a command resets the navigation position."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q MSFT")

        history.previous()  # Q MSFT
        history.previous()  # Q AAPL

        history.add("W")  # Adding new command should reset position

        assert history.previous() == "W"  # Should start from newest

    def test_duplicate_consecutive_commands_not_added(self):
        """Test that duplicate consecutive commands are not added."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q AAPL")  # Duplicate, should not be added
        history.add("Q AAPL")  # Duplicate, should not be added

        assert history.previous() == "Q AAPL"
        assert history.previous() == "Q AAPL"  # Only one entry

    def test_empty_commands_not_added(self):
        """Test that empty or whitespace-only commands are not added."""
        history = CommandHistory(max_size=10)
        history.add("")
        history.add("   ")
        history.add("Q AAPL")

        assert history.previous() == "Q AAPL"
        assert history.previous() == "Q AAPL"  # No empty entries

    def test_reset_clears_position(self):
        """Test that reset() clears the navigation position."""
        history = CommandHistory(max_size=10)
        history.add("Q AAPL")
        history.add("Q MSFT")

        history.previous()  # Q MSFT
        history.previous()  # Q AAPL
        history.reset()

        assert history.previous() == "Q MSFT"  # Back to most recent
