"""Centralized manager for discovering and installing Omnigent integrations and extras."""

from __future__ import annotations

import importlib.util
import logging
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class ExtraInfo:
    """Metadata for an official Omnigent extra or integration package."""
    name: str
    title: str
    description: str
    module_name: str
    subdirectory: str
    remote_url: str

    @property
    def package_name(self) -> str:
        """PyPI / pip distribution name."""
        return self.module_name.replace("_", "-")


# Official catalog of modular integrations in Omnigent
_OFFICIAL_CATALOG: list[ExtraInfo] = [
    ExtraInfo(
        name="telegram",
        title="Telegram Bot Integration",
        description="Drives Omnigent chat sessions from Telegram with streaming responses and inline approvals.",
        module_name="omnigent_telegram",
        subdirectory="integrations/telegram",
        remote_url="git+https://github.com/Daleth-Barreto/omnigent.git@main#subdirectory=integrations/telegram",
    ),
    ExtraInfo(
        name="slack",
        title="Slack Socket-Mode Integration",
        description="Socket-mode Slack bot daemon for collaborative agent workflows in channels.",
        module_name="omnigent_slack",
        subdirectory="integrations/slack",
        remote_url="git+https://github.com/Daleth-Barreto/omnigent.git@main#subdirectory=integrations/slack",
    ),
]


def get_catalog() -> list[ExtraInfo]:
    """Return the official list of available extras/integrations."""
    return list(_OFFICIAL_CATALOG)


def get_extra(name: str) -> ExtraInfo | None:
    """Find an ExtraInfo by short name (e.g., 'telegram' or 'slack')."""
    name_lower = name.lower().strip()
    for extra in _OFFICIAL_CATALOG:
        if extra.name == name_lower or extra.module_name == name_lower:
            return extra
    return None


def is_installed(extra: ExtraInfo | str) -> bool:
    """Check if the integration module is currently installed in the Python environment."""
    module_name = extra.module_name if isinstance(extra, ExtraInfo) else extra
    # Handle short names if a string was passed
    if isinstance(extra, str):
        info = get_extra(extra)
        if info:
            module_name = info.module_name
    try:
        spec = importlib.util.find_spec(module_name)
        return spec is not None
    except (ImportError, ValueError, AttributeError):
        return False


def get_installer_command(
    extra: ExtraInfo | str,
    uninstall: bool = False,
    use_uv: bool | None = None,
) -> list[str]:
    """Build the command-line argument list to install or uninstall an extra."""
    info = extra if isinstance(extra, ExtraInfo) else get_extra(extra)
    if not info:
        raise ValueError(f"Unknown extra or integration: {extra}")

    if use_uv is None:
        use_uv = shutil.which("uv") is not None

    if uninstall:
        if use_uv:
            return ["uv", "pip", "uninstall", "--python", sys.executable, "-y", info.package_name]
        return [sys.executable, "-m", "pip", "uninstall", "-y", info.package_name]

    # Check if we are inside a local git checkout / repo with the subdirectory
    repo_root = Path(__file__).resolve().parent.parent
    local_dir = repo_root / info.subdirectory
    if not local_dir.exists():
        # Fallback to checking current working directory
        local_dir = Path.cwd() / info.subdirectory

    if local_dir.exists() and (local_dir / "pyproject.toml").exists():
        target = f"-e{str(local_dir)}"
    else:
        target = info.remote_url

    if use_uv:
        return ["uv", "pip", "install", "--python", sys.executable, target]
    return [sys.executable, "-m", "pip", "install", target]


def run_installer(
    extra_name: str,
    uninstall: bool = False,
    stream_callback: Callable[[str], None] | None = None,
) -> tuple[int, str]:
    """Execute installation or uninstallation of an extra, streaming output if requested."""
    cmd = get_installer_command(extra_name, uninstall=uninstall)
    logger.info("Running installer command: %s", " ".join(cmd))
    if stream_callback:
        stream_callback(f">> Running command: {' '.join(cmd)}\n")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except Exception as exc:
        err_msg = f"Failed to start installer subprocess: {exc}"
        if stream_callback:
            stream_callback(f"[ERROR] {err_msg}\n")
        return 1, err_msg

    output_lines: list[str] = []
    if process.stdout:
        for line in process.stdout:
            output_lines.append(line)
            if stream_callback:
                stream_callback(line)

    process.wait()
    returncode = process.returncode
    final_output = "".join(output_lines)

    if returncode == 0:
        msg = f"\n[SUCCESS] {'Uninstallation' if uninstall else 'Installation'} of '{extra_name}' completed."
    else:
        msg = f"\n[FAILED] Command exited with return code {returncode}."

    if stream_callback:
        stream_callback(f"{msg}\n")

    return returncode, final_output
