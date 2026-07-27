# Omnigent Telegram Bot (`omnigent-telegram`)

A standalone Telegram Bot integration for Omnigent that enables natural conversational interactions, progressive streaming responses, tool approvals via inline keyboards, and persistent session storage.

## Features
- **Natural Conversational Flow:** Users can chat directly with Omnigent agents via Telegram DMs or group threads.
- **Progressive Streaming:** Uses Telegram's `editMessageText` API to stream AI response deltas in real-time.
- **Inline Keyboards for Tool Approvals:** Renders interactive buttons for tool execution approvals and multiple-choice questions (elicitations).
- **Persistent SQLite Storage:** Maps `(chat_id, thread_id)` pairs to persistent Omnigent server sessions.

## Configuration
Set the following environment variables (or configure via a `.env` file):

```bash
TELEGRAM_BOT_TOKEN="your-telegram-bot-token"
OMNIGENT_SERVER_URL="http://localhost:8000"
SQLITE_DB_PATH="~/.omnigent/telegram_sessions.db"
```

## Running the Bot
```bash
# Install package in editable mode
pip install -e integrations/telegram

# Run the bot module
python -m omnigent_telegram
```
