# holodok_agent/bot/scheduler.py
from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import BaseStorage, StorageKey
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from holodok_agent.bot.handlers import MetricsFlow

MONTHLY_METRICS_PROMPT = (
    "Итоги месяца: сколько новых заявок пришло и сколько времени, по ощущениям, "
    "сэкономил бот? Ответьте одним сообщением, например: «5 заявок, часа 3 в неделю»."
)


async def send_monthly_metrics_prompt(bot: Bot, owner_id: int, storage: BaseStorage) -> None:
    key = StorageKey(bot_id=bot.id, chat_id=owner_id, user_id=owner_id)
    state = FSMContext(storage=storage, key=key)
    await state.set_state(MetricsFlow.waiting_for_monthly_answer)
    await bot.send_message(owner_id, MONTHLY_METRICS_PROMPT)


def schedule_monthly_metrics_prompt(
    scheduler: AsyncIOScheduler, bot: Bot, owner_id: int, storage: BaseStorage
) -> None:
    scheduler.add_job(
        send_monthly_metrics_prompt,
        trigger=CronTrigger(day=1, hour=10, minute=0),
        args=[bot, owner_id, storage],
        id="monthly_metrics_prompt",
        replace_existing=True,
    )
