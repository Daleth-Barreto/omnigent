"""Entry point for running the Omnigent Telegram Bot."""

import asyncio
import logging
import sys

from omnigent_telegram.bot import OmnigentTelegramBot
from omnigent_telegram.config import TelegramConfig


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )
    try:
        config = TelegramConfig()
    except Exception as exc:
        logging.error("Failed to load Telegram bot configuration: %s", exc)
        logging.error("Please set TELEGRAM_BOT_TOKEN environment variable or check your .env file.")
        sys.exit(1)

    bot = OmnigentTelegramBot(config)
    try:
        asyncio.run(bot.start())
    except KeyboardInterrupt:
        logging.info("Telegram Bot shut down cleanly by user.")
    except Exception as exc:
        logging.critical("Fatal error running Telegram Bot: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
