"""Unit tests for the Omnigent extras and integrations manager."""

from __future__ import annotations

import importlib.util
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from omnigent.cli import cli
from omnigent.extras_manager import (
    ExtraInfo,
    get_catalog,
    get_extra,
    get_installer_command,
    is_installed,
)


def test_get_catalog_and_get_extra() -> None:
    """Verify that official catalog contains expected extras and lookup works."""
    catalog = get_catalog()
    assert len(catalog) >= 2
    names = {e.name for e in catalog}
    assert "telegram" in names
    assert "slack" in names

    telegram_info = get_extra("telegram")
    assert telegram_info is not None
    assert telegram_info.module_name == "omnigent_telegram"
    assert telegram_info.package_name == "omnigent-telegram"

    assert get_extra("nonexistent") is None


def test_is_installed_mocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify is_installed behavior with mocked find_spec."""
    def mock_find_spec(name: str) -> Any | None:
        if name == "omnigent_telegram":
            return MagicMock()
        return None

    monkeypatch.setattr(importlib.util, "find_spec", mock_find_spec)
    assert is_installed("telegram") is True
    assert is_installed("slack") is False


def test_get_installer_command(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify command generation for uv vs pip and install vs uninstall."""
    info = get_extra("telegram")
    assert info is not None

    # Test uv uninstall
    cmd_uv_un = get_installer_command("telegram", uninstall=True, use_uv=True)
    assert cmd_uv_un == ["uv", "pip", "uninstall", "-y", "omnigent-telegram"]

    # Test pip uninstall
    cmd_pip_un = get_installer_command("telegram", uninstall=True, use_uv=False)
    assert "uninstall" in cmd_pip_un and "omnigent-telegram" in cmd_pip_un

    # Test uv install (when local subdirectory exists in dev workspace)
    cmd_uv_in = get_installer_command("telegram", uninstall=False, use_uv=True)
    assert cmd_uv_in[0] == "uv"
    assert cmd_uv_in[1] == "pip"
    assert cmd_uv_in[2] == "install"


def test_integration_list_cli() -> None:
    """Verify integration list command executes cleanly in Click CliRunner."""
    runner = CliRunner()
    result = runner.invoke(cli, ["integration", "list"])
    assert result.exit_code == 0
    assert "Omnigent Official Integrations & Extras" in result.output
    assert "telegram" in result.output
    assert "slack" in result.output
