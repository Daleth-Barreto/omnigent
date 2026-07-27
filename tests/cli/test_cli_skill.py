"""Unit tests for omnigent skill CLI commands."""

import json
from pathlib import Path
import pytest
import yaml
from click.testing import CliRunner

from omnigent.cli import cli
from omnigent.cli_skill import _load_registry


def test_load_built_in_registry() -> None:
    registry = _load_registry()
    assert "skills" in registry
    names = [s["name"] for s in registry["skills"]]
    assert "context7" in names
    assert "playwright" in names
    assert "testsprite" in names


def test_skill_search_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "search", "context7", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) >= 1
    assert data[0]["name"] == "context7"


def test_skill_list_command() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["skill", "list", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data) >= 3


def test_skill_install_and_remove_agent(tmp_path: Path) -> None:
    agent_file = tmp_path / "config.yaml"
    agent_file.write_text("name: test_agent\ntools: {}\n", encoding="utf-8")

    runner = CliRunner()
    # Install
    res_inst = runner.invoke(cli, ["skill", "install", "playwright", "--agent", str(agent_file)])
    assert res_inst.exit_code == 0, res_inst.output
    assert "Successfully wired 'playwright'" in res_inst.output

    data = yaml.safe_load(agent_file.read_text("utf-8"))
    assert "playwright" in data["tools"]
    assert data["tools"]["playwright"]["type"] == "mcp"
    assert data["tools"]["playwright"]["command"] == "npx"

    # List wired
    res_list = runner.invoke(cli, ["skill", "list", "--agent", str(agent_file), "--json"])
    assert res_list.exit_code == 0
    list_data = json.loads(res_list.output)
    assert any(item["name"] == "playwright" for item in list_data)

    # Remove
    res_rem = runner.invoke(cli, ["skill", "remove", "playwright", "--agent", str(agent_file)])
    assert res_rem.exit_code == 0, res_rem.output
    assert "Removed 'playwright'" in res_rem.output

    data_after = yaml.safe_load(agent_file.read_text("utf-8"))
    assert "playwright" not in data_after.get("tools", {})
