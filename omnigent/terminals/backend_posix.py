"""POSIX terminal backend implementation using tmux and PTY."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Callable

from omnigent.terminals.backend import TerminalBackend

logger = logging.getLogger(__name__)


class PosixTmuxBackend(TerminalBackend):
    """Terminal backend for Linux, macOS, and WSL environments using tmux."""

    def __init__(self, socket_dir: Path | None = None) -> None:
        self.socket_dir = socket_dir or Path("/tmp/omnigent_tmux_sockets")
        self.socket_dir.mkdir(parents=True, exist_ok=True)
        self._instances: dict[str, Any] = {}

    def _get_socket_path(self, session_key: str) -> Path:
        return self.socket_dir / f"tmux_{session_key}.sock"

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
        """Spawn a new tmux session running the given command."""
        socket_path = self._get_socket_path(session_key)
        if not shutil.which("tmux"):
            raise RuntimeError("tmux binary not found in PATH; required for POSIX terminal backend.")

        cmd_list = ["tmux", "-S", str(socket_path), "new-session", "-d", "-s", session_key, "-n", name]
        if cwd:
            cmd_list.extend(["-c", str(cwd)])
        
        full_cmd = command
        if args:
            full_cmd = f"{command} {' '.join(args)}"
        cmd_list.append(full_cmd)

        spawn_env = os.environ.copy()
        if env:
            spawn_env.update(env)

        res = subprocess.run(cmd_list, env=spawn_env, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            logger.error("Failed to spawn tmux session %s: %s", session_key, res.stderr)
            raise RuntimeError(f"tmux spawn failed: {res.stderr}")

        self._instances[session_key] = {"socket": socket_path, "name": name, "command": full_cmd}
        if on_output:
            self._start_reader_thread(session_key, on_output)
        return self._instances[session_key]

    def _start_reader_thread(self, session_key: str, on_output: Callable[[str], None]) -> None:
        def _read_loop() -> None:
            last_content = ""
            while session_key in self._instances:
                content = self.capture_pane(session_key, lines=100)
                if content != last_content and not content.startswith("*"):
                    last_content = content
                    on_output(content)
                time.sleep(0.5)

        threading.Thread(target=_read_loop, daemon=True).start()

    def send_keys(
        self,
        session_key: str,
        text: str = "",
        literal: bool = True,
        keys: list[str] | None = None,
    ) -> None:
        """Send keystrokes to the tmux session."""
        socket_path = self._get_socket_path(session_key)
        if not socket_path.exists():
            raise RuntimeError(f"Session socket {socket_path} does not exist.")

        if text:
            cmd = ["tmux", "-S", str(socket_path), "send-keys", "-t", session_key]
            if literal:
                cmd.append("-l")
            cmd.append(text)
            subprocess.run(cmd, check=True)

        if keys:
            cmd_keys = ["tmux", "-S", str(socket_path), "send-keys", "-t", session_key]
            cmd_keys.extend(keys)
            subprocess.run(cmd_keys, check=True)

    def capture_pane(self, session_key: str, lines: int | None = None) -> str:
        """Capture visible text or scrollback from the tmux pane."""
        socket_path = self._get_socket_path(session_key)
        if not socket_path.exists():
            return "*Terminal socket offline or session terminated.*"

        cmd = ["tmux", "-S", str(socket_path), "capture-pane", "-t", session_key, "-p"]
        if lines is not None:
            cmd.extend(["-S", f"-{lines}"])
        
        res = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if res.returncode != 0:
            return f"*Failed to capture pane: {res.stderr}*"
        return res.stdout

    def resize(self, session_key: str, cols: int, rows: int) -> None:
        """Resize the tmux window dimensions."""
        socket_path = self._get_socket_path(session_key)
        if not socket_path.exists():
            return
        cmd = [
            "tmux",
            "-S",
            str(socket_path),
            "resize-window",
            "-t",
            session_key,
            "-x",
            str(cols),
            "-y",
            str(rows),
        ]
        subprocess.run(cmd, check=False)

    def terminate(self, session_key: str) -> None:
        """Kill the tmux session and remove socket."""
        socket_path = self._get_socket_path(session_key)
        if socket_path.exists():
            cmd = ["tmux", "-S", str(socket_path), "kill-session", "-t", session_key]
            subprocess.run(cmd, check=False)
            try:
                socket_path.unlink(missing_ok=True)
            except Exception:
                pass
        self._instances.pop(session_key, None)
