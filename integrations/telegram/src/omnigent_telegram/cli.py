"""CLI command group for managing the Omnigent Telegram bot integration."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import click
import httpx

from omnigent_telegram.bot import OmnigentTelegramBot
from omnigent_telegram.config import TelegramConfig

_logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """Return the path to the Telegram configuration file."""
    return Path.home() / ".omnigent" / "telegram_config.json"


def load_saved_config() -> dict[str, Any] | None:
    """Load saved Telegram configuration from disk if available."""
    path = get_config_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except (OSError, ValueError) as exc:
        _logger.warning("Failed to read Telegram configuration file %s: %s", path, exc)
    return None


def save_config(data: dict[str, Any]) -> None:
    """Save Telegram configuration to disk."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _validate_telegram_token(token: str) -> str:
    """Validate token via Telegram getMe API and return the bot username."""
    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        response = httpx.get(url, timeout=10.0)
    except httpx.HTTPError as exc:
        raise click.ClickException(
            f"Network error while connecting to Telegram API: {exc}"
        ) from exc

    if response.status_code != 200:
        raise click.ClickException(
            "Authentication failed with Telegram API. Please check your bot token."
        )

    try:
        data = response.json()
    except (ValueError, TypeError) as exc:
        raise click.ClickException("Failed to parse response from Telegram API.") from exc

    if not data.get("ok"):
        raise click.ClickException("Telegram API rejected the token as invalid.")

    result = data.get("result", {})
    username = result.get("username")
    if not isinstance(username, str) or not username:
        return "UnknownBot"
    return username


def _do_setup(token: str | None, server_url: str) -> None:
    if not token:
        click.echo("Telegram Bot Setup Instructions:")
        click.echo("  Step 1: Open Telegram and search for @BotFather.")
        click.echo("  Step 2: Send /newbot and follow the prompts to create your bot.")
        click.echo("  Step 3: Copy the HTTP API Token provided by BotFather.")
        click.echo()
        token = click.prompt("Enter your Telegram Bot Token", type=str)

    token = token.strip()
    if not token:
        raise click.ClickException("Bot token cannot be empty.")

    click.echo("Validating bot token with Telegram...")
    username = _validate_telegram_token(token)
    click.echo(f"Successfully authenticated as @{username}!")

    config_data = {
        "telegram_bot_token": token,
        "omnigent_server_url": server_url.strip(),
        "bot_username": username,
    }
    save_config(config_data)
    click.echo(f"Configuration saved to {get_config_path()}.")


def _do_start() -> None:
    saved = load_saved_config()
    token = (saved.get("telegram_bot_token") if saved else None) or os.environ.get(
        "TELEGRAM_BOT_TOKEN"
    )
    if not token:
        raise click.ClickException(
            "Telegram bot is not configured. Run 'omnigent telegram setup' first."
        )

    server_url = (saved.get("omnigent_server_url") if saved else None) or "http://localhost:6767"
    username = (saved.get("bot_username") if saved else None) or "TelegramBot"

    config = TelegramConfig(
        telegram_bot_token=token,
        omnigent_server_url=server_url,
    )
    bot = OmnigentTelegramBot(config)

    click.echo(f"Starting Telegram bot @{username}... Press Ctrl+C to stop.")
    try:
        bot.start()
    except KeyboardInterrupt:
        click.echo("\nStopped Telegram bot.")


def _do_status() -> None:
    saved = load_saved_config()
    if not saved or not saved.get("telegram_bot_token"):
        click.echo("Status: Not configured. Run 'omnigent telegram setup' first.")
        return

    username = saved.get("bot_username", "Unknown")
    url = saved.get("omnigent_server_url", "http://localhost:6767")
    click.echo("Status: Configured")
    click.echo(f"Bot Username: @{username}")
    click.echo(f"Server URL: {url}")
    click.echo(f"Config File: {get_config_path()}")


def _do_reset() -> None:
    path = get_config_path()
    if path.exists():
        try:
            path.unlink()
            click.echo("Removed Telegram bot configuration.")
        except OSError as exc:
            raise click.ClickException(f"Failed to remove configuration file: {exc}") from exc
    else:
        click.echo("No Telegram bot configuration found.")


@click.group("telegram")
def telegram_cli() -> None:
    """Manage Telegram bot integration and registration."""


@telegram_cli.command("setup")
@click.option("--token", help="Telegram Bot API token.")
@click.option("--server-url", default="http://localhost:6767", help="Omnigent server URL.")
def setup_cmd(token: str | None, server_url: str) -> None:
    """Register and configure the Telegram bot."""
    _do_setup(token, server_url)


@telegram_cli.command("register")
@click.option("--token", help="Telegram Bot API token.")
@click.option("--server-url", default="http://localhost:6767", help="Omnigent server URL.")
def register_cmd(token: str | None, server_url: str) -> None:
    """Alias for setup: register and configure the Telegram bot."""
    _do_setup(token, server_url)


@telegram_cli.command("start")
def start_cmd() -> None:
    """Start the configured Telegram bot."""
    _do_start()


@telegram_cli.command("run")
def run_cmd() -> None:
    """Alias for start: start the configured Telegram bot."""
    _do_start()


@telegram_cli.command("status")
def status_cmd() -> None:
    """Show the current configuration status of the Telegram bot."""
    _do_status()


@telegram_cli.command("reset")
def reset_cmd() -> None:
    """Remove the saved Telegram bot configuration."""
    _do_reset()


@telegram_cli.command("remove")
def remove_cmd() -> None:
    """Alias for reset: remove the saved Telegram bot configuration."""
    _do_reset()
