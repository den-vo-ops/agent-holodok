# holodok_agent/bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from holodok_agent.bot.handlers import build_router
from holodok_agent.config import load_config
from holodok_agent.db import connect
from holodok_agent.llm.client import ClaudeClient


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    config = load_config()
    conn = connect(config.db_path)
    claude_client = ClaudeClient(api_key=config.anthropic_api_key, model=config.anthropic_model)

    bot = Bot(token=config.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["conn"] = conn
    dp["claude_client"] = claude_client
    dp["owner_id"] = config.owner_telegram_id
    dp.include_router(build_router(config.owner_telegram_id))

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
