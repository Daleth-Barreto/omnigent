"""Unit tests for TelegramSQLiteStore."""

from pathlib import Path

import pytest
from omnigent_telegram.store import ChatThreadKey, TelegramSQLiteStore


@pytest.mark.asyncio
async def test_telegram_store_crud(tmp_path: Path) -> None:
    db_path = tmp_path / "test_telegram.db"
    store = TelegramSQLiteStore(db_path)
    await store.initialize()

    key = ChatThreadKey(chat_id=12345, thread_id=0)

    # Initially empty
    session = await store.get_session(key)
    assert session is None

    # Upsert
    await store.upsert_session(key, "sess_abc", "Test Chat 12345", owner_user_id="user_1")
    session = await store.get_session(key)
    assert session is not None
    assert session.session_id == "sess_abc"
    assert session.owner_user_id == "user_1"

    # Update session id
    await store.upsert_session(key, "sess_xyz", "Test Chat 12345 Updated")
    session_updated = await store.get_session(key)
    assert session_updated is not None
    assert session_updated.session_id == "sess_xyz"
    assert session_updated.owner_user_id == "user_1"  # Preserved via COALESCE

    # Delete
    await store.delete_session(key)
    session_deleted = await store.get_session(key)
    assert session_deleted is None
