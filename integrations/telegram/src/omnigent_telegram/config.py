"""Configuration settings for the Omnigent Telegram integration."""

from __future__ import annotations

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramConfig(BaseSettings):
    """Configuration loaded from environment variables or .env file."""
    
    telegram_bot_token: str
    omnigent_server_url: str = "http://localhost:8000"
    sqlite_db_path: Path = Path.home() / ".omnigent" / "telegram_sessions.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
