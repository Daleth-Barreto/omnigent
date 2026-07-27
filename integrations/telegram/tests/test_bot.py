"""Unit tests for OmnigentTelegramBot keyboard formatting and config."""

from pathlib import Path
import pytest
from telegram import InlineKeyboardMarkup

from omnigent_telegram.bot import OmnigentTelegramBot
from omnigent_telegram.config import TelegramConfig
from omnigent_telegram.events import ElicitationOption, ElicitationQuestion, ElicitationRequest


def test_telegram_config_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    config = TelegramConfig()
    assert config.telegram_bot_token == "12345:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert config.omnigent_server_url == "http://localhost:8000"


def test_build_elicitation_keyboard_binary(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token")
    config = TelegramConfig(sqlite_db_path=tmp_path / "test.db")
    bot = OmnigentTelegramBot(config)

    elicit = ElicitationRequest(questions=[])
    kb = bot._build_elicitation_keyboard("elicit_101", elicit)
    assert isinstance(kb, InlineKeyboardMarkup)
    assert len(kb.inline_keyboard) == 1
    buttons = kb.inline_keyboard[0]
    assert len(buttons) == 2
    assert buttons[0].text == "✅ Approve"
    assert buttons[0].callback_data == "elicit:elicit_101:approve"
    assert buttons[1].text == "❌ Deny"
    assert buttons[1].callback_data == "elicit:elicit_101:deny"


def test_build_elicitation_keyboard_form(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake_token")
    config = TelegramConfig(sqlite_db_path=tmp_path / "test.db")
    bot = OmnigentTelegramBot(config)

    q1 = ElicitationQuestion(
        key="color",
        question="Choose a color",
        options=[
            ElicitationOption(label="Red"),
            ElicitationOption(label="Blue"),
        ],
    )
    elicit = ElicitationRequest(questions=[q1])
    kb = bot._build_elicitation_keyboard("elicit_202", elicit)
    assert len(kb.inline_keyboard) == 2
    assert kb.inline_keyboard[0][0].text == "👉 Red"
    assert kb.inline_keyboard[0][0].callback_data == "elicit:elicit_202:opt:color:Red"
    assert kb.inline_keyboard[1][0].text == "👉 Blue"
    assert kb.inline_keyboard[1][0].callback_data == "elicit:elicit_202:opt:color:Blue"
