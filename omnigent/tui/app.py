"""Core Textual application and client bridge for the universal Omnigent TUI."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Input

from omnigent.terminals.backend import get_terminal_backend
from omnigent.tui.views import ElicitationModal, IntegrationsPane, LogsPane, SessionsSidebar, TerminalPane

logger = logging.getLogger(__name__)


class OmnigentTUI(App[None]):
    """Universal Textual TUI for orchestrating and monitoring Omnigent agents and terminals."""

    TITLE = "Omnigent Universal Console (TUI)"
    SUB_TITLE = "Cross-Platform Terminal & Session Orchestrator"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+s", "toggle_sidebar", "Toggle Sidebar", show=True, priority=True),
        Binding("ctrl+l", "toggle_logs", "Toggle Logs", show=True, priority=True),
        Binding("ctrl+n", "new_session", "New Session", show=True, priority=True),
        Binding("ctrl+e", "toggle_integrations", "Extras / Integrations", show=True, priority=True),
        Binding("f2", "toggle_integrations", "Extras (F2)", show=False, priority=True),
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
            yield IntegrationsPane()
        yield LogsPane()
        yield Footer()

    def on_mount(self) -> None:
        """Called when TUI is mounted; starts periodic session syncing and local terminal."""
        self.query_one(LogsPane).log_event(
            f"Initialized TUI connecting to {self.server_url} using backend: {self.backend.__class__.__name__}"
        )
        self._refresh_timer = self.set_interval(5.0, self.refresh_sessions_task)
        self.run_worker(self._initial_load())
        self.action_new_session()
        try:
            self.query_one("#terminal-input", Input).focus()
        except Exception:
            pass

    async def _initial_load(self) -> None:
        """Initial background load of sessions."""
        try:
            # We dynamically import or mock client connect if server is offline during TUI start
            from omnigent_client import OmnigentClient
            client = OmnigentClient(base_url=self.server_url)
            sessions = await client.sessions.list()
            if sessions:
                self.query_one(SessionsSidebar).update_sessions(list(sessions))
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

        def _on_output(text: str) -> None:
            def _update() -> None:
                try:
                    self.query_one(TerminalPane).write_ansi(text)
                except Exception:
                    pass
            self.call_from_thread(_update)

        try:
            inst = self.backend.spawn(
                "tui-session",
                "tui-1",
                "bash" if self.backend.__class__.__name__ == "PosixTmuxBackend" else "powershell.exe",
                on_output=_on_output,
            )
            pane.write_ansi(f"[bold green]Session spawned successfully via {self.backend.__class__.__name__}![/bold green]\n")
            self.query_one(LogsPane).log_event(f"Spawned local terminal: {inst}")
        except Exception as exc:
            pane.write_ansi(f"[bold red]Spawn failed:[/bold red] {exc}\n")
            self.query_one(LogsPane).log_event(f"Spawn error: {exc}")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command submitted from the terminal input box."""
        if event.input.id == "terminal-input":
            command = event.value.strip()
            if not command:
                return
            event.input.value = ""
            pane = self.query_one(TerminalPane)
            pane.write_ansi(f"[bold cyan]> {command}[/bold cyan]\n")
            try:
                self.backend.send_keys("tui-1", text=command)
                self.query_one(LogsPane).log_event(f"Sent command to terminal: {command}")
            except Exception as exc:
                pane.write_ansi(f"[bold red]Error sending command:[/bold red] {exc}\n")
                self.query_one(LogsPane).log_event(f"Send error: {exc}")

    def trigger_elicitation(self, prompt: str, elicit_id: str) -> None:
        """Helper to show the approval modal screen from a background worker."""
        def _show() -> None:
            self.push_screen(ElicitationModal(prompt=prompt, elicit_id=elicit_id))
        self.call_from_thread(_show)

    def action_toggle_integrations(self) -> None:
        """Toggle visibility of the Integrations/Extras manager pane vs Terminal pane."""
        term_pane = self.query_one(TerminalPane)
        int_pane = self.query_one(IntegrationsPane)
        if int_pane.display:
            int_pane.display = False
            term_pane.display = True
        else:
            term_pane.display = False
            int_pane.display = True
            int_pane.refresh_catalog()
            self.query_one(LogsPane).log_event("Opened Integrations & Extras Manager.")

    def on_button_pressed(self, event: Any) -> None:
        """Handle buttons pressed in the IntegrationsPane or modals."""
        btn_id = getattr(event.button, "id", "")
        if btn_id in ("btn-install-extra", "btn-uninstall-extra", "btn-install-all"):
            from omnigent.extras_manager import get_catalog, run_installer
            int_pane = self.query_one(IntegrationsPane)
            logs = self.query_one(LogsPane)
            if not logs.display:
                logs.display = True

            if btn_id == "btn-install-all":
                targets = [e.name for e in get_catalog()]
                uninstall = False
            else:
                selected = int_pane.get_selected_extra_name()
                if not selected:
                    logs.log_event("[WARNING] Please select an integration from the list first.")
                    return
                targets = [selected]
                uninstall = (btn_id == "btn-uninstall-extra")

            def _worker() -> None:
                for t in targets:
                    logs.log_event(f"Starting {'uninstallation' if uninstall else 'installation'} of '{t}'...")
                    def _stream(msg: str) -> None:
                        self.call_from_thread(lambda: logs.log_event(msg.strip()))
                    run_installer(t, uninstall=uninstall, stream_callback=_stream)
                self.call_from_thread(lambda: int_pane.refresh_catalog())

            import threading
            threading.Thread(target=_worker, daemon=True).start()


def run_tui(server_url: str = "http://127.0.0.1:6767") -> None:
    """Launch the universal interactive TUI."""
    app = OmnigentTUI(server_url=server_url)
    app.run()

