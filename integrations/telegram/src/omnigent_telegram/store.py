"""SQLite storage for Telegram chat and thread session mappings."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import aiosqlite


@dataclass(frozen=True, slots=True)
class ChatThreadKey:
    """Unique key identifying a Telegram chat and optional message topic thread."""

    chat_id: int
    thread_id: int = 0


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """Record of an active Omnigent session mapped to a Telegram chat/thread."""

    session_id: str
    owner_user_id: str | None = None
    host_id: str | None = None
    workspace: str | None = None


class TelegramSQLiteStore:
    """Persistent SQLite session mapping for Telegram bot."""

    def __init__(self, path: Path) -> None:
        self._path = path

    async def initialize(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS telegram_sessions (
                    chat_id INTEGER NOT NULL,
                    thread_id INTEGER NOT NULL DEFAULT 0,
                    omnigent_session_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    owner_user_id TEXT,
                    host_id TEXT,
                    workspace TEXT,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    PRIMARY KEY (chat_id, thread_id)
                )
                """
            )
            await db.commit()

    async def get_session(self, key: ChatThreadKey) -> SessionRecord | None:
        async with aiosqlite.connect(self._path) as db:
            cursor = await db.execute(
                """
                SELECT omnigent_session_id, owner_user_id, host_id, workspace
                FROM telegram_sessions
                WHERE chat_id = ? AND thread_id = ?
                """,
                (key.chat_id, key.thread_id),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if row is None:
            return None
        return SessionRecord(
            session_id=str(row[0]),
            owner_user_id=str(row[1]) if row[1] is not None else None,
            host_id=str(row[2]) if row[2] is not None else None,
            workspace=str(row[3]) if row[3] is not None else None,
        )

    async def upsert_session(
        self,
        key: ChatThreadKey,
        session_id: str,
        title: str,
        *,
        owner_user_id: str | None = None,
        host_id: str | None = None,
        workspace: str | None = None,
    ) -> None:
        now = int(time.time())
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                """
                INSERT INTO telegram_sessions (
                    chat_id, thread_id, omnigent_session_id,
                    title, owner_user_id, host_id, workspace,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chat_id, thread_id) DO UPDATE SET
                    omnigent_session_id = excluded.omnigent_session_id,
                    title = excluded.title,
                    owner_user_id = COALESCE(
                        excluded.owner_user_id, telegram_sessions.owner_user_id
                    ),
                    host_id = COALESCE(excluded.host_id, telegram_sessions.host_id),
                    workspace = COALESCE(excluded.workspace, telegram_sessions.workspace),
                    updated_at = excluded.updated_at
                """,
                (
                    key.chat_id,
                    key.thread_id,
                    session_id,
                    title,
                    owner_user_id,
                    host_id,
                    workspace,
                    now,
                    now,
                ),
            )
            await db.commit()

    async def delete_session(self, key: ChatThreadKey) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "DELETE FROM telegram_sessions WHERE chat_id = ? AND thread_id = ?",
                (key.chat_id, key.thread_id),
            )
            await db.commit()
