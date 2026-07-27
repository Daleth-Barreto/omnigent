"""Core Textual application and client bridge for the universal Omnigent TUI."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header

from omnigent.terminals.backend import get_terminal_backend
from omnigent.tui.views import ElicitationModal, LogsPane, SessionsSidebar, TerminalPane

logger = logging.getLogger(__name__)


class OmnigentTUI(App[None]):
    """Universal Textual TUI for orchestrating and monitoring Omnigent agents and terminals."""

    TITLE = "Omnigent Universal Console (TUI)"
    SUB_TITLE = "Cross-Platform Terminal & Session Orchestrator"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+s", "toggle_sidebar", "Toggle Sidebar", show=True),
        Binding("ctrl+l", "toggle_logs", "Toggle Logs", show=True),
        Binding("ctrl+n", "new_session", "New Session", show=True),
    ]

    def __init__(self, server_url: str = "http://127.0.0.1:6767", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.server_url = server_url
        self.backend = get_terminal_backend()
        self.active_session_id: str | None = None
        self._refresh_timer: Any = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield SessionsSidebar()
            yield TerminalPane()
        yield LogsPane()
        yield Footer()

    def on_mount(self) -> None:
        """Called when TUI is mounted; starts periodic session syncing."""
        self.query_one(LogsPane).log_event(
            f"Initialized TUI connecting to {self.server_url} using backend: {self.backend.__class__.__name__}"
        )
        self._refresh_timer = self.set_interval(5.0, self.refresh_sessions_task)
        self.run_worker(self._initial_load())

    async def _initial_load(self) -> None:
        """Initial background load of sessions."""
        try:
            # We dynamically import or mock client connect if server is offline during TUI start
            from omnigent_client import OmnigentClient
            client = OmnigentClient(base_url=self.server_url)
            sessions = await client.list_sessions()
            if isinstance(sessions, list):
                self.query_one(SessionsSidebar).update_sessions(sessions)
                self.query_one(LogsPane).log_event(f"Loaded {len(sessions)} active sessions from server.")
        except Exception as exc:
            self.query_one(LogsPane).log_event(f"Offline mode / server unreachable: {exc}")
            # Show a demo offline session so TUI is usable even without active daemon
            self.query_one(SessionsSidebar).update_sessions([
                {"id": "local-posix-shell", "title": "Local Terminal Shell", "status": "Ready"}
            ])

    def refresh_sessions_task(self) -> None:
        """Periodic background task to sync session state."""
        self.run_worker(self._initial_load(), exclusive=True)

    def action_toggle_sidebar(self) -> None:
        """Toggle visibility of the sessions sidebar."""
        sidebar = self.query_one(SessionsSidebar)
        sidebar.display = not sidebar.display

    def action_toggle_logs(self) -> None:
        """Toggle visibility of the bottom diagnostic log pane."""
        logs = self.query_one(LogsPane)
        logs.display = not logs.display

    def action_new_session(self) -> None:
        """Create a new interactive session in the terminal pane."""
        pane = self.query_one(TerminalPane)
        pane.clear_pane()
        pane.write_ansi("[bold yellow]Spawning new terminal session...[/bold yellow]\n")
        try:
            inst = self.backend.spawn("tui-session", "tui-1", "bash" if self.backend.__class__.__name__ == "PosixTmuxBackend" else "powershell.exe")
            pane.write_ansi(f"[bold green]Session spawned successfully via {self.backend.__class__.__name__}![/bold green]\n")
            self.query_one(LogsPane).log_event(f"Spawned local terminal: {inst}")
        except Exception as exc:
            pane.write_ansi(f"[bold red]Spawn failed:[/bold red] {exc}\n")
            self.query_one(LogsPane).log_event(f"Spawn error: {exc}")

    def trigger_elicitation(self, prompt: str, elicit_id: str) -> None:
        """Helper to show the approval modal screen from a background worker."""
        def _show() -> None:
            self.push_screen(ElicitationModal(prompt=prompt, elicit_id=elicit_id))
        self.call_from_thread(_show)
