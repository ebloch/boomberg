"""Boomberg-style command bar widget."""

from dataclasses import dataclass

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.events import Key
from textual.message import Message
from textual.widgets import Input, Static

from boomberg.ui.command_history import CommandHistory


class CommandBar(Static):
    """Boomberg-style command input bar."""

    HISTORY_SIZE = 50

    DEFAULT_CSS = """
    CommandBar {
        height: 3;
        dock: bottom;
        background: $surface;
        border-top: solid $primary;
    }

    CommandBar Horizontal {
        height: 100%;
        padding: 0 1;
    }

    CommandBar #prompt {
        width: auto;
        padding: 1 1 1 0;
        color: $secondary;
    }

    CommandBar Input {
        width: 1fr;
        border: none;
        background: transparent;
    }

    CommandBar Input:focus {
        border: none;
    }
    """

    @dataclass
    class CommandSubmitted(Message):
        """Message sent when a command is submitted."""

        command: str
        args: list[str]

        @property
        def raw(self) -> str:
            """Get the raw command string."""
            parts = [self.command] + self.args
            return " ".join(parts)

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._history = CommandHistory(max_size=self.HISTORY_SIZE)

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static(">", id="prompt")
            yield Input(placeholder="Q AAPL, WEI, TOP, MOST, WB, FXIP, ECST, GP, FA, FI, N, W, S, ? for help")

    @on(Input.Submitted)
    def handle_submit(self, event: Input.Submitted) -> None:
        """Handle command submission."""
        raw = event.value.strip()
        if not raw:
            return

        self._history.add(raw)

        parts = raw.split()
        command = parts[0].upper()
        args = parts[1:] if len(parts) > 1 else []

        self.post_message(self.CommandSubmitted(command=command, args=args))
        event.input.clear()

    def on_key(self, event: Key) -> None:
        """Handle key events for history navigation."""
        input_widget = self.query_one(Input)

        if event.key == "up":
            cmd = self._history.previous()
            input_widget.value = cmd
            input_widget.cursor_position = len(cmd)
            event.prevent_default()
            event.stop()
        elif event.key == "down":
            cmd = self._history.next()
            input_widget.value = cmd
            input_widget.cursor_position = len(cmd)
            event.prevent_default()
            event.stop()

    def focus_input(self) -> None:
        """Focus the command input."""
        self.query_one(Input).focus()
