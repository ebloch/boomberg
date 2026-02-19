"""Command history for terminal-like navigation."""

from collections import deque


class CommandHistory:
    """Stores and navigates through command history.

    Supports terminal-like up/down arrow navigation through previous commands.
    """

    def __init__(self, max_size: int = 100):
        """Initialize command history.

        Args:
            max_size: Maximum number of commands to store.
        """
        self._history: deque[str] = deque(maxlen=max_size)
        self._position: int = -1  # -1 means "not navigating", at the input line

    def add(self, command: str) -> None:
        """Add a command to history.

        Empty commands and consecutive duplicates are ignored.
        Adding a command resets the navigation position.

        Args:
            command: The command string to add.
        """
        command = command.strip()
        if not command:
            return

        # Don't add consecutive duplicates
        if self._history and self._history[-1] == command:
            self.reset()
            return

        self._history.append(command)
        self.reset()

    def previous(self) -> str:
        """Navigate to the previous (older) command.

        Returns:
            The previous command, or empty string if at the beginning or empty.
        """
        if not self._history:
            return ""

        if self._position == -1:
            # Start navigating from the most recent
            self._position = len(self._history) - 1
        elif self._position > 0:
            # Move to older command
            self._position -= 1
        # else: stay at oldest (position 0)

        return self._history[self._position]

    def next(self) -> str:
        """Navigate to the next (newer) command.

        Returns:
            The next command, or empty string if at the end (back to input line).
        """
        if not self._history or self._position == -1:
            return ""

        if self._position < len(self._history) - 1:
            # Move to newer command
            self._position += 1
            return self._history[self._position]
        else:
            # Back to the input line
            self._position = -1
            return ""

    def reset(self) -> None:
        """Reset navigation position to the end (input line)."""
        self._position = -1
