"""Textual UI views and components for the universal Omnigent TUI."""

from __future__ import annotations

from typing import Any

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label, ListItem, ListView, RichLog, Static



class SessionListItem(ListItem):
    """List item representing a single agent chat session."""

    def __init__(self, session_id: str, title: str, status: str = "Idle", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.session_id = session_id
        self.title_text = title
        self.status = status

    def compose(self) -> ComposeResult:
        yield Label(f"[bold]{self.title_text}[/bold]\n[dim]ID: {self.session_id[:8]}... | Status: {self.status}[/dim]")


class SessionsSidebar(Vertical):
    """Sidebar widget displaying all active server sessions."""

    DEFAULT_CSS = """
    SessionsSidebar {
        width: 30;
        dock: left;
        background: $panel;
        border-right: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]Active Sessions[/bold cyan]", classes="sidebar-title")
        yield ListView(id="sessions-list")

    def update_sessions(self, sessions: list[dict[str, Any]]) -> None:
        """Update the list view with current sessions from the server."""
        list_view = self.query_one("#sessions-list", ListView)
        list_view.clear()
        for s in sessions:
            sid = str(s.get("id", "unknown"))
            title = str(s.get("title", f"Session {sid[:6]}"))
            status = str(s.get("status", "Running"))
            list_view.append(SessionListItem(session_id=sid, title=title, status=status))


class TerminalPane(Container):
    """Main live ANSI terminal viewer and agent interaction pane."""

    DEFAULT_CSS = """
    TerminalPane {
        height: 1fr;
        border: solid $accent;
        background: $surface;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold green]Terminal Output (Active Pane)[/bold green]", id="pane-title")
        yield RichLog(id="terminal-log", highlight=True, markup=True)

    def write_ansi(self, text: str) -> None:
        """Append ANSI text to the log viewer."""
        log_widget = self.query_one("#terminal-log", RichLog)
        log_widget.write(text)

    def clear_pane(self) -> None:
        """Clear the terminal log view."""
        log_widget = self.query_one("#terminal-log", RichLog)
        log_widget.clear()


class LogsPane(Container):
    """Bottom collapsible log pane for diagnostics and tool inspection."""

    DEFAULT_CSS = """
    LogsPane {
        height: 10;
        dock: bottom;
        background: $boost;
        border-top: solid $secondary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[dim]System & MCP Tool Diagnostics Log[/dim]")
        yield RichLog(id="system-log", markup=True)

    def log_event(self, message: str) -> None:
        """Append a diagnostic event message."""
        log_widget = self.query_one("#system-log", RichLog)
        log_widget.write(f"[dim]{message}[/dim]")


class ElicitationModal(ModalScreen[bool]):
    """Modal screen displayed when an agent requires human approval or elicitation."""

    DEFAULT_CSS = """
    ElicitationModal {
        align: center middle;
    }
    #modal-dialog {
        width: 60;
        height: auto;
        border: thick $warning;
        background: $surface;
        padding: 1 2;
    }
    #modal-buttons {
        margin-top: 1;
        align: center middle;
    }
    """

    def __init__(self, prompt: str, elicit_id: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.prompt = prompt
        self.elicit_id = elicit_id

    def compose(self) -> ComposeResult:
        with Container(id="modal-dialog"):
            yield Label(f"[bold yellow]Agent Action Required (ID: {self.elicit_id})[/bold yellow]\n")
            yield Label(self.prompt)
            with Horizontal(id="modal-buttons"):
                yield Button("Approve (Y)", variant="success", id="btn-approve")
                yield Button("Deny (N)", variant="error", id="btn-deny")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-approve":
            self.dismiss(True)
        else:
            self.dismiss(False)
