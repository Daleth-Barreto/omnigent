"""Unit tests for the omnigent tui CLI command and Textual app instantiation."""

from unittest.mock import patch

from click.testing import CliRunner
from omnigent.cli import cli
from omnigent.tui import OmnigentTUI


def test_tui_cli_registration():
    """Verify that tui is registered in the main Click CLI."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "tui" in result.output


def test_tui_app_instantiation():
    """Verify OmnigentTUI initializes properly with given server URL."""
    app = OmnigentTUI(server_url="http://test-server:1234")
    assert app.server_url == "http://test-server:1234"
    assert app.TITLE == "Omnigent Universal Console (TUI)"


def test_tui_cli_invocation():
    """Test invoking omnigent tui via Click runner."""
    runner = CliRunner()
    with patch.object(OmnigentTUI, "run") as mock_run:
        result = runner.invoke(cli, ["tui", "--server", "http://localhost:9999"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
