"""Telegram Bot implementation for driving Omnigent sessions."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from omnigent_telegram.config import TelegramConfig
from omnigent_telegram.events import (
    ElicitationRequest,
    extract_delta,
    extract_elicitation_request,
    is_hard_terminal_event,
)
from omnigent_telegram.omnigent import OmnigentClient, RunnerUnavailableError
from omnigent_telegram.store import ChatThreadKey, TelegramSQLiteStore

logger = logging.getLogger(__name__)


class OmnigentTelegramBot:
    """Telegram bot instance driving Omnigent sessions with streaming and approvals."""

    def __init__(self, config: TelegramConfig) -> None:
        self.config = config
        self.store = TelegramSQLiteStore(config.sqlite_db_path)
        self.client = OmnigentClient(base_url=config.omnigent_server_url)
        self.app: Optional[Application] = None

    async def initialize(self) -> None:
        """Initialize SQLite storage and check connection to Omnigent server."""
        await self.store.initialize()
        try:
            await self.client.check_health()
            logger.info("Connected to Omnigent server at %s", self.config.omnigent_server_url)
        except Exception as exc:
            logger.warning("Could not verify Omnigent server liveness during init: %s", exc)

    def build_application(self) -> Application:
        """Build and configure the telegramext Application."""
        self.app = ApplicationBuilder().token(self.config.telegram_bot_token).build()

        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("new", self.cmd_new))
        self.app.add_handler(CommandHandler("status", self.cmd_status))
        self.app.add_handler(CallbackQueryHandler(self.on_callback, pattern="^elicit:"))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.on_message))

        return self.app

    async def start(self) -> None:
        """Start the Telegram bot polling loop."""
        await self.initialize()
        app = self.build_application()
        logger.info("Starting Omnigent Telegram Bot polling...")
        await app.run_polling()

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /start command."""
        msg = (
            "🤖 **Welcome to Omnigent Bot**\n\n"
            "I am connected to the autonomous agent server. Send any message to converse or ask me to perform tasks (e.g., research, clone repos, run tests).\n\n"
            "**Available Commands:**\n"
            "/new - Reset chat session and start fresh on the server.\n"
            "/status - View connection status and active session ID.\n"
            "/help - Show this help message."
        )
        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /help command."""
        await self.cmd_start(update, context)

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /status command."""
        if not update.effective_chat:
            return
        key = ChatThreadKey(update.effective_chat.id, update.effective_message.message_thread_id or 0 if update.effective_message else 0)
        record = await self.store.get_session(key)
        
        status_msg = f"🌐 **Omnigent Server:** `{self.config.omnigent_server_url}`\n"
        if record:
            status_msg += f"🔑 **Active Session:** `{record.session_id}`"
        else:
            status_msg += "ℹ️ **Session:** None active (will be created on next message)."
            
        if update.message:
            await update.message.reply_text(status_msg, parse_mode="Markdown")

    async def cmd_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /new command — resets chat session."""
        if not update.effective_chat:
            return
        key = ChatThreadKey(update.effective_chat.id, update.effective_message.message_thread_id or 0 if update.effective_message else 0)
        await self.store.delete_session(key)
        if update.message:
            await update.message.reply_text("🔄 **Session reset.** Your next message will create a fresh session on the server.", parse_mode="Markdown")

    async def _ensure_session(self, key: ChatThreadKey) -> str:
        """Retrieve existing session ID or create a fresh session on the Omnigent server."""
        record = await self.store.get_session(key)
        if record:
            return record.session_id

        agents = await self.client.list_agents()
        agent_id = "daleth-agent"
        if agents and isinstance(agents, list) and len(agents) > 0:
            agent_id = agents[0].get("id", agent_id)

        session_id = await self.client.create_session(agent_id, title=f"Telegram Chat {key.chat_id}")
        await self.store.upsert_session(key, session_id, title=f"Telegram Chat {key.chat_id}")
        return session_id

    def _build_elicitation_keyboard(self, elicit_id: str, elicit: ElicitationRequest) -> InlineKeyboardMarkup:
        buttons = []
        if not elicit.questions:
            buttons.append([
                InlineKeyboardButton("✅ Approve", callback_data=f"elicit:{elicit_id}:approve"),
                InlineKeyboardButton("❌ Deny", callback_data=f"elicit:{elicit_id}:deny"),
            ])
        else:
            for q in elicit.questions:
                for opt in q.options:
                    buttons.append([
                        InlineKeyboardButton(f"👉 {opt.label}", callback_data=f"elicit:{elicit_id}:opt:{q.key}:{opt.label}")
                    ])
        return InlineKeyboardMarkup(buttons)

    async def on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for normal text messages — streams turn to/from Omnigent server."""
        if not update.effective_chat or not update.message or not update.message.text:
            return

        chat_id = update.effective_chat.id
        thread_id = update.message.message_thread_id or 0
        key = ChatThreadKey(chat_id, thread_id)

        try:
            session_id = await self._ensure_session(key)
        except Exception as exc:
            logger.error("Failed to ensure session for chat %s: %s", chat_id, exc)
            await update.message.reply_text(f"⚠️ **Server connection error:**\n`{exc}`", parse_mode="Markdown")
            return

        status_msg = await update.message.reply_text("⏳ *Processing request...*", parse_mode="Markdown")

        text_buffer = ""
        last_edit_time = 0.0
        
        try:
            async for event in self.client.run_turn(session_id, update.message.text):
                delta = extract_delta(event)
                if delta:
                    text_buffer += delta
                    now = time.time()
                    if now - last_edit_time > 1.5 and text_buffer.strip():
                        try:
                            await status_msg.edit_text(text_buffer[:4090])
                            last_edit_time = now
                        except Exception:
                            pass

                elicit = extract_elicitation_request(event)
                if elicit:
                    elicit_id = event.get("data", {}).get("id", "default_elicit")
                    keyboard = self._build_elicitation_keyboard(elicit_id, elicit)
                    prompt_text = text_buffer if text_buffer.strip() else "⚠️ **Action required by agent:**"
                    if elicit.questions:
                        for q in elicit.questions:
                            prompt_text += f"\n\n❓ **{q.question}**"
                    try:
                        await status_msg.edit_text(prompt_text[:4090], reply_markup=keyboard, parse_mode="Markdown")
                    except Exception:
                        await status_msg.edit_text(prompt_text[:4090], reply_markup=keyboard)
                    return

                if is_hard_terminal_event(event):
                    break

            final_text = text_buffer.strip() or "✅ *Turn completed with no text output.*"
            try:
                await status_msg.edit_text(final_text[:4090], parse_mode="Markdown")
            except Exception:
                await status_msg.edit_text(final_text[:4090])

        except Exception as exc:
            logger.error("Error during streaming turn in session %s: %s", session_id, exc)
            err_text = f"⚠️ **Error during turn execution:**\n`{exc}`"
            if text_buffer:
                err_text = text_buffer[:3500] + "\n\n" + err_text
            try:
                await status_msg.edit_text(err_text[:4090], parse_mode="Markdown")
            except Exception:
                await update.message.reply_text(err_text[:4090], parse_mode="Markdown")

    async def on_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for InlineKeyboard button clicks (elicitation resolutions)."""
        query = update.callback_query
        if not query:
            return
        await query.answer()

        data = query.data or ""
        parts = data.split(":")
        if len(parts) < 3:
            return

        elicit_id = parts[1]
        action = parts[2]

        chat_id = update.effective_chat.id if update.effective_chat else 0
        thread_id = update.effective_message.message_thread_id or 0 if update.effective_message else 0
        key = ChatThreadKey(chat_id, thread_id)

        record = await self.store.get_session(key)
        if not record or not query.message:
            await query.edit_message_text("⚠️ Session expired or not found.")
            return

        accepted = (action == "approve" or action == "opt")
        content = None
        verdict_text = ""

        if action == "approve":
            verdict_text = "\n\n✅ **Approved by user.**"
        elif action == "deny":
            accepted = False
            verdict_text = "\n\n❌ **Denied by user.**"
        elif action == "opt" and len(parts) >= 5:
            q_key = parts[3]
            selected_label = ":".join(parts[4:])
            content = {q_key: selected_label}
            verdict_text = f"\n\n✅ **Selected: {selected_label}**"

        try:
            await self.client.resolve_elicitation(
                record.session_id,
                elicit_id,
                accepted=accepted,
                content=content,
            )
            current_text = query.message.text or ""
            await query.edit_message_text((current_text + verdict_text)[:4090], reply_markup=None, parse_mode="Markdown")
        except Exception as exc:
            logger.error("Failed to resolve elicitation %s: %s", elicit_id, exc)
            await query.edit_message_text(f"⚠️ Error sending response to server: `{exc}`", reply_markup=None, parse_mode="Markdown")
