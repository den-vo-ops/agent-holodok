# tests/test_scheduler.py
from unittest.mock import AsyncMock, MagicMock

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from holodok_agent.bot.scheduler import (
    MONTHLY_METRICS_PROMPT,
    schedule_monthly_metrics_prompt,
    send_monthly_metrics_prompt,
)


def test_schedule_monthly_metrics_prompt_registers_first_of_month_job():
    scheduler = AsyncIOScheduler()
    bot = MagicMock()
    storage = MagicMock()

    schedule_monthly_metrics_prompt(scheduler, bot, owner_id=123, storage=storage)

    job = scheduler.get_job("monthly_metrics_prompt")
    assert job is not None
    assert isinstance(job.trigger, CronTrigger)


async def test_send_monthly_metrics_prompt_sets_state_and_sends_message(monkeypatch):
    bot = MagicMock()
    bot.id = 999
    bot.send_message = AsyncMock()
    storage = MagicMock()

    captured = {}

    class FakeFSMContext:
        def __init__(self, storage, key):
            captured["key"] = key

        async def set_state(self, state):
            captured["state"] = state

    monkeypatch.setattr("holodok_agent.bot.scheduler.FSMContext", FakeFSMContext)

    await send_monthly_metrics_prompt(bot, owner_id=123, storage=storage)

    assert captured["key"].chat_id == 123
    assert captured["key"].user_id == 123
    bot.send_message.assert_awaited_once_with(123, MONTHLY_METRICS_PROMPT)
