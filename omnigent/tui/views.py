"""Textual UI views and components for the universal Omnigent TUI."""

from __future__ import annotations

from typing import Any

from rich.console import RenderableType
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, RichLog, Static



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

    def update_sessions(self, sessions: list[Any]) -> None:
        """Update the list view with current sessions from the server."""
        list_view = self.query_one("#sessions-list", ListView)
        list_view.clear()
        for s in sessions:
            if isinstance(s, dict):
                sid = str(s.get("id", "unknown"))
                title = str(s.get("title", f"Session {sid[:6]}"))
                status = str(s.get("status", "Running"))
            else:
                sid = str(getattr(s, "id", getattr(s, "session_id", "unknown")))
                title = str(getattr(s, "title", f"Session {sid[:6]}"))
                status = str(getattr(s, "status", "Running"))
            list_view.append(SessionListItem(session_id=sid, title=title, status=status))


class TerminalPane(Container):
    """Main live ANSI terminal viewer and agent interaction pane."""

    DEFAULT_CSS = """
    TerminalPane {
        height: 1fr;
        border: solid $accent;
        background: $surface;
        layout: vertical;
    }
    #pane-title {
        dock: top;
        height: auto;
        padding: 0 1;
        background: $boost;
    }
    #terminal-log {
        height: 1fr;
        width: 100%;
    }
    #terminal-input {
        dock: bottom;
        width: 100%;
        margin-top: 1;
        border: solid $primary;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._output_buffer = ""
        self._flush_timer: Any = None

    def compose(self) -> ComposeResult:
        yield Label("[bold green]Terminal Output (Active Pane)[/bold green]", id="pane-title")
        yield RichLog(id="terminal-log", highlight=True, markup=True)
        yield Input(
            placeholder="Escribe tu comando aquí (ej: opencode, dir, omnigent --help) y presiona Enter...",
            id="terminal-input",
        )

    def write_ansi(self, text: str) -> None:
        """Append ANSI text to the log viewer, coalescing incomplete lines."""
        log_widget = self.query_one("#terminal-log", RichLog)
        if "[" in text and "/" in text and any(tag in text for tag in ("bold", "green", "red", "yellow", "cyan", "dim")):
            log_widget.write(text)
            return

        self._output_buffer += text
        if "\n" in self._output_buffer:
            lines = self._output_buffer.split("\n")
            for line in lines[:-1]:
                log_widget.write(Text.from_ansi(line.rstrip("\r")))
            self._output_buffer = lines[-1]
            if self._flush_timer:
                self._flush_timer.stop()
                self._flush_timer = None

        if self._output_buffer and not self._flush_timer:
            self._flush_timer = self.set_timer(0.05, self._flush_pending_buffer)

    def _flush_pending_buffer(self) -> None:
        if self._output_buffer:
            log_widget = self.query_one("#terminal-log", RichLog)
            log_widget.write(Text.from_ansi(self._output_buffer.rstrip("\r")))
            self._output_buffer = ""
        self._flush_timer = None

    def clear_pane(self) -> None:
        """Clear the terminal log view."""
        self._output_buffer = ""
        if self._flush_timer:
            self._flush_timer.stop()
            self._flush_timer = None
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


class ExtraListItem(ListItem):
    """List item representing an official extra/integration in the TUI."""

    def __init__(self, name: str, title: str, description: str, installed: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.extra_name = name
        self.title_text = title
        self.desc_text = description
        self.installed = installed

    def compose(self) -> ComposeResult:
        status_color = "green" if self.installed else "yellow"
        status_text = "INSTALLED" if self.installed else "NOT INSTALLED"
        yield Label(f"[bold]{self.title_text}[/bold] ([bold {status_color}]{status_text}[/bold {status_color}])\n[dim]{self.desc_text}[/dim]")


class IntegrationsPane(Container):
    """Pane for viewing and managing official Omnigent integrations and extras."""

    DEFAULT_CSS = """
    IntegrationsPane {
        height: 1fr;
        border: solid $secondary;
        background: $surface;
        padding: 1 2;
        display: none;
    }
    #extras-actions {
        height: auto;
        margin-top: 1;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Label("[bold cyan]Gestor de Integraciones & Extras Oficiales[/bold cyan]\n[dim]Selecciona una integración para ver acciones o administrar paquetes:[/dim]", id="extras-title")
        yield ListView(id="extras-list")
        with Horizontal(id="extras-actions"):
            yield Button("Instalar / Actualizar Extra", variant="primary", id="btn-install-extra")
            yield Button("Desinstalar Extra", variant="warning", id="btn-uninstall-extra")
            yield Button("Instalar TODOS", variant="success", id="btn-install-all")

    def refresh_catalog(self) -> None:
        from omnigent.extras_manager import get_catalog, is_installed
        list_view = self.query_one("#extras-list", ListView)
        list_view.clear()
        for extra in get_catalog():
            list_view.append(ExtraListItem(name=extra.name, title=extra.title, description=extra.description, installed=is_installed(extra)))

    def get_selected_extra_name(self) -> str | None:
        list_view = self.query_one("#extras-list", ListView)
        if list_view.highlighted_child and isinstance(list_view.highlighted_child, ExtraListItem):
            return list_view.highlighted_child.extra_name
        return None

