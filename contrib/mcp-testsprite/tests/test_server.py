"""Unit tests for mcp-testsprite server wrapper."""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch
from mcp_testsprite.server import testsprite_check, testsprite_run


@pytest.mark.asyncio
async def test_testsprite_check_invalid_dir(tmp_path: Path) -> None:
    non_existent = str(tmp_path / "does_not_exist")
    res = await testsprite_check(cwd=non_existent)
    assert "no existe o no es válido" in res


@pytest.mark.asyncio
async def test_testsprite_check_valid_dir(tmp_path: Path) -> None:
    res = await testsprite_check(cwd=str(tmp_path))
    assert "=== TestSprite Status Report" in res


@pytest.mark.asyncio
async def test_testsprite_run_invalid_dir(tmp_path: Path) -> None:
    non_existent = str(tmp_path / "does_not_exist")
    res = await testsprite_run(cwd=non_existent)
    assert "no existe" in res


@pytest.mark.asyncio
async def test_testsprite_run_mocked_execution(tmp_path: Path) -> None:
    with patch("mcp_testsprite.server.shutil.which") as mock_which, \
         patch("mcp_testsprite.server._run_subprocess", new_callable=AsyncMock) as mock_subproc:
        mock_which.side_effect = lambda bin_name: "/usr/bin/npx" if bin_name == "npx" else None
        mock_subproc.return_value = (0, "TestSprite generated 5 tests successfully.", "")
        
        res = await testsprite_run(cwd=str(tmp_path), command="test", args=["--verbose"])
        
        mock_subproc.assert_called_once()
        assert "=== TestSprite Execution:" in res
        assert "Código de salida (return code): 0" in res
        assert "TestSprite generated 5 tests successfully." in res
