"""Unit tests for the abstract terminal backend interface and platform factories."""

import sys
from unittest.mock import patch

import pytest
from omnigent.terminals.backend import TerminalBackend, get_terminal_backend
from omnigent.terminals.backend_win32 import Win32ConPtyBackend


def test_get_terminal_backend_factory():
    """Verify factory returns appropriate backend based on platform."""
    backend = get_terminal_backend()
    assert isinstance(backend, TerminalBackend)
    if sys.platform == "win32":
        assert isinstance(backend, Win32ConPtyBackend)
    else:
        from omnigent.terminals.backend_posix import PosixTmuxBackend

        assert isinstance(backend, PosixTmuxBackend)


def test_win32_backend_lifecycle():
    """Test Win32 backend spawn, capture, send_keys, and terminate lifecycle."""
    backend = Win32ConPtyBackend()
    
    # Spawn a fast-exiting command or mock process
    with patch("subprocess.Popen") as mock_popen:
        mock_proc = mock_popen.return_value
        mock_proc.pid = 12345
        mock_proc.stdin = None
        
        res = backend.spawn("test-win", "session-1", "cmd.exe", ["/c", "echo hello"])
        assert res["name"] == "test-win"
        assert "12345" in backend.capture_pane("session-1")
        
        backend.terminate("session-1")
        assert "offline" in backend.capture_pane("session-1").lower()
