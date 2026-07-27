"""Win32 ConPTY and subprocess fallback terminal backend for native Windows."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
from pathlib import Path
from typing import Any, Callable

from omnigent.terminals.backend import TerminalBackend

logger = logging.getLogger(__name__)


class Win32ConPtyBackend(TerminalBackend):
    """Terminal backend for Windows bare-metal environments using subprocessing / ConPTY."""

    def __init__(self) -> None:
        self._instances: dict[str, dict[str, Any]] = {}

    def spawn(
        self,
        name: str,
        session_key: str,
        command: str = "powershell.exe",
        args: list[str] | None = None,
        env: dict[str, str] | None = None,
        cwd: str | Path | None = None,
        on_output: Callable[[str], None] | None = None,
    ) -> Any:
        """Spawn a Windows subprocess or ConPTY session."""
        full_cmd = [command]
        if args:
            full_cmd.extend(args)

        spawn_env = os.environ.copy()
        if env:
            spawn_env.update(env)

        try:
            proc = subprocess.Popen(
                full_cmd,
                env=spawn_env,
                cwd=str(cwd) if cwd else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                bufsize=0,
            )
            self._instances[session_key] = {
                "process": proc,
                "name": name,
                "command": command,
                "buffer": [f"[Win32 Terminal: {name} spawned with PID {proc.pid}]\n"],
            }
            self._start_reader_thread(proc, self._instances[session_key], on_output)
            return self._instances[session_key]
        except Exception as exc:
            logger.error("Failed to spawn Win32 terminal process %s: %s", session_key, exc)
            raise RuntimeError(f"Win32 spawn failed: {exc}") from exc

    def _start_reader_thread(
        self,
        proc: subprocess.Popen[Any],
        inst: dict[str, Any],
        on_output: Callable[[str], None] | None,
    ) -> None:
        def _read_loop() -> None:
            stdout = proc.stdout
            if not stdout:
                return
            while True:
                try:
                    data = os.read(stdout.fileno(), 4096)
                    if not data:
                        break
                    text = data.decode("utf-8", errors="replace").replace("\r\n", "\n").replace("\r", "")
                    inst["buffer"].append(text)
                    if len(inst["buffer"]) > 2000:
                        inst["buffer"] = inst["buffer"][-2000:]
                    if on_output:
                        on_output(text)
                except (OSError, ValueError):
                    break
            if on_output:
                on_output("\n[bold red]*Terminal process terminated*[/bold red]\n")

        threading.Thread(target=_read_loop, daemon=True).start()

    def send_keys(
        self,
        session_key: str,
        text: str = "",
        literal: bool = True,
        keys: list[str] | None = None,
    ) -> None:
        """Send input to the stdin of the Win32 subprocess."""
        inst = self._instances.get(session_key)
        if not inst or not inst.get("process"):
            raise RuntimeError(f"Win32 session {session_key} is not running.")
        proc: subprocess.Popen[Any] = inst["process"]
        if proc.stdin and text:
            clean_text = text.rstrip("\r\n") + "\r\n"
            proc.stdin.write(clean_text.encode("utf-8") if isinstance(clean_text, str) else clean_text)
            proc.stdin.flush()

    def capture_pane(self, session_key: str, lines: int | None = None) -> str:
        """Capture output buffer from the Win32 subprocess."""
        inst = self._instances.get(session_key)
        if not inst:
            return "*Win32 Terminal session offline.*"
        buf = inst.get("buffer", [])
        if lines and len(buf) > lines:
            return "\n".join(buf[-lines:])
        return "\n".join(buf)

    def resize(self, session_key: str, cols: int, rows: int) -> None:
        """Resize operation placeholder for Win32 Console."""
        # In Phase 2, this will adjust ConPTY dimensions via Win32 API.
        pass

    def terminate(self, session_key: str) -> None:
        """Terminate the Win32 process."""
        inst = self._instances.pop(session_key, None)
        if inst and inst.get("process"):
            try:
                inst["process"].terminate()
            except Exception:
                pass
