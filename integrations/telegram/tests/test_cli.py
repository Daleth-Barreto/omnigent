"""Unit tests for the Telegram bot CLI command group."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
from click.testing import CliRunner
from omnigent_telegram.cli import load_saved_config, telegram_cli


@pytest.fixture(autouse=True)
def mock_config_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    config_file = tmp_path / "telegram_config.json"
    monkeypatch.setattr("omnigent_telegram.cli.get_config_path", lambda: config_file)
    return config_file


class MockResponse:
    def __init__(self, status_code: int, json_data: dict[str, Any]) -> None:
        self.status_code = status_code
        self._json_data = json_data

    def json(self) -> dict[str, Any]:
        return self._json_data


def test_telegram_status_unconfigured(runner: CliRunner | None = None) -> None:
    runner = runner or CliRunner()
    result = runner.invoke(telegram_cli, ["status"])
    assert result.exit_code == 0
    assert "Status: Not configured. Run 'omnigent telegram setup' first." in result.output


def test_telegram_setup_valid_token(
    monkeypatch: pytest.MonkeyPatch, mock_config_path: Path
) -> None:
    def mock_get(url: str, timeout: float) -> MockResponse:  # noqa: ARG001
        assert "fake_token_123" in url
        return MockResponse(200, {"ok": True, "result": {"username": "DalethBot"}})

    monkeypatch.setattr(httpx, "get", mock_get)

    runner = CliRunner()
    result = runner.invoke(
        telegram_cli,
        ["setup", "--token", "fake_token_123", "--server-url", "http://testserver:9000"],
    )
    assert result.exit_code == 0
    assert "Successfully authenticated as @DalethBot!" in result.output
    assert "Configuration saved to" in result.output

    assert mock_config_path.exists()
    saved = load_saved_config()
    assert saved is not None
    assert saved["telegram_bot_token"] == "fake_token_123"
    assert saved["omnigent_server_url"] == "http://testserver:9000"
    assert saved["bot_username"] == "DalethBot"


def test_telegram_setup_invalid_token(
    monkeypatch: pytest.MonkeyPatch, mock_config_path: Path
) -> None:
    def mock_get(url: str, timeout: float) -> MockResponse:  # noqa: ARG001
        return MockResponse(200, {"ok": False})

    monkeypatch.setattr(httpx, "get", mock_get)

    runner = CliRunner()
    result = runner.invoke(telegram_cli, ["setup", "--token", "invalid_token"])
    assert result.exit_code != 0
    assert "Telegram API rejected the token as invalid." in result.output
    assert not mock_config_path.exists()


def test_telegram_status_configured(
    monkeypatch: pytest.MonkeyPatch,
    mock_config_path: Path,  # noqa: ARG001
) -> None:
    mock_config_path.write_text(
        json.dumps(
            {
                "telegram_bot_token": "token_xyz",
                "omnigent_server_url": "http://localhost:8000",
                "bot_username": "AwesomeAgentBot",
            }
        ),
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(telegram_cli, ["status"])
    assert result.exit_code == 0
    assert "Status: Configured" in result.output
    assert "Bot Username: @AwesomeAgentBot" in result.output
    assert "Server URL: http://localhost:8000" in result.output


def test_telegram_reset_and_remove(mock_config_path: Path) -> None:
    mock_config_path.write_text("{}", encoding="utf-8")
    assert mock_config_path.exists()

    runner = CliRunner()
    result = runner.invoke(telegram_cli, ["reset"])
    assert result.exit_code == 0
    assert "Removed Telegram bot configuration." in result.output
    assert not mock_config_path.exists()

    result2 = runner.invoke(telegram_cli, ["remove"])
    assert result2.exit_code == 0
    assert "No Telegram bot configuration found." in result2.output
