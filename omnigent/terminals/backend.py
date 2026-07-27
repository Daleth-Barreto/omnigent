"""Abstract Terminal Backend interface for cross-platform session multiplexing and TUI control."""

from __future__ import annotations

import abc
import sys
from pathlib import Path
from typing import Any, Callable

class TerminalBackend(abc.ABC):
    """Abstract base class defining universal terminal control operations."""

    @abc.abstractmethod
    def spawn(
        self,
        name: str,
        session_key: str,
        command: str = "bash",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> Any:
        """Spawn a new terminal session or process."""

    @abc.abstractmethod
    def send_keys(
        self,
        session_key: str,
        text: str = "",
        literal: bool = True,
        keys: list[str] | None = None,
    ) -> None:
        """Send text and keystrokes directly to the target terminal TTY."""

    @abc.abstractmethod
    def capture_pane(self, session_key: str, lines: int | None = None) -> str:
        """Capture the current viewport or scrollback output of the target terminal."""

    @abc.abstractmethod
    def resize(self, session_key: str, cols: int, rows: int) -> None:
        """Resize the target terminal dimensions (columns x rows)."""

    @abc.abstractmethod
    def terminate(self, session_key: str) -> None:
        """Terminate the target terminal session and clean up sockets/resources."""


def get_terminal_backend() -> TerminalBackend:
    """Factory returning the platform-appropriate terminal backend."""
    if sys.platform == "win32":
        from omnigent.terminals.backend_win32 import Win32ConPtyBackend

        return Win32ConPtyBackend()
    else:
        from omnigent.terminals.backend_posix import PosixTmuxBackend

        return PosixTmuxBackend()
