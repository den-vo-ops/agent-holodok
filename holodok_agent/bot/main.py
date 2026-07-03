# holodok_agent/bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from holodok_agent.bot.handlers import build_router
from holodok_agent.bot.scheduler import schedule_monthly_metrics_prompt
from holodok_agent.config import load_config
from holodok_agent.db import connect
from holodok_agent.llm.client import ClaudeClient
from holodok_agent.llm.errors import FALLBACK_MESSAGE

logger = logging.getLogger(__name__)


async def handle_global_error(event: ErrorEvent, bot: Bot, owner_id: int) -> None:
    """Safety net for anything not already caught by a handler's own LLMError handling.

    Must never itself raise: this is the last line of defense against a silent bot.
    """
    logger.error(
        "Unhandled error while processing update %s",
        event.update.update_id,
        exc_info=event.exception,
    )
    try:
        await bot.send_message(owner_id, FALLBACK_MESSAGE)
    except Exception:
        logger.exception("Failed to notify owner about an unhandled error")


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
    dp.errors.register(handle_global_error)

    scheduler = AsyncIOScheduler()
    schedule_monthly_metrics_prompt(scheduler, bot, config.owner_telegram_id, dp.storage)
    scheduler.start()

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
