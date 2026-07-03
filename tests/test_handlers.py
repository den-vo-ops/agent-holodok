# tests/test_handlers.py
from unittest.mock import AsyncMock, MagicMock

from holodok_agent.bot.handlers import (
    Onboarding,
    ScenarioFlow,
    handle_start,
    handle_onboarding_sample,
    handle_onboarding_done,
    handle_remember_rule,
    handle_publish,
)


async def test_handle_start_prompts_onboarding_when_no_style_profile(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr("holodok_agent.bot.handlers.db.get_style_profile", lambda c: None)

    await handle_start(message, state, conn)

    state.set_state.assert_awaited_once_with(Onboarding.waiting_for_samples)
    message.answer.assert_awaited_once()


async def test_handle_start_shows_menu_when_style_profile_exists(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    conn = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.get_style_profile",
        lambda c: {"tone_summary": "t", "lexicon_notes": "l", "structure_notes": "s"},
    )

    await handle_start(message, state, conn)

    state.set_state.assert_not_called()
    message.answer.assert_awaited_once()
    _, kwargs = message.answer.call_args
    assert "reply_markup" in kwargs


async def test_handle_onboarding_sample_appends_to_state():
    message = MagicMock()
    message.text = "старый текст объявления"
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"samples": ["первый"]})
    state.update_data = AsyncMock()

    await handle_onboarding_sample(message, state)

    state.update_data.assert_awaited_once_with(samples=["первый", "старый текст объявления"])


async def test_handle_onboarding_done_rejects_when_no_samples():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"samples": []})
    conn = MagicMock()
    claude_client = MagicMock()

    await handle_onboarding_done(message, state, conn, claude_client)

    message.answer.assert_awaited_once_with("Пришли хотя бы один текст перед /done.")


async def test_handle_onboarding_done_saves_profile_and_clears_state(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"samples": ["текст 1"]})
    state.clear = AsyncMock()
    conn = MagicMock()
    claude_client = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.analyze_style",
        lambda client, samples: {"tone_summary": "t", "lexicon_notes": "l", "structure_notes": "s"},
    )
    saved = {}
    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.save_style_profile",
        lambda c, tone, lex, struct, samples: saved.update(tone=tone, samples=samples),
    )

    await handle_onboarding_done(message, state, conn, claude_client)

    state.clear.assert_awaited_once()
    assert saved == {"tone": "t", "samples": ["текст 1"]}
    assert message.answer.await_count == 2


async def test_handle_remember_rule_saves_rule(monkeypatch):
    message = MagicMock()
    message.text = "запомни, никогда не демпинговать"
    message.answer = AsyncMock()
    conn = MagicMock()
    saved = {}

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.add_hard_rule",
        lambda c, rule: saved.setdefault("rule", rule),
    )

    await handle_remember_rule(message, conn)

    assert saved["rule"] == "никогда не демпинговать"
    message.answer.assert_awaited_once_with("Запомнил: никогда не демпинговать")


async def test_handle_remember_rule_rejects_empty_rule():
    message = MagicMock()
    message.text = "запомни"
    message.answer = AsyncMock()
    conn = MagicMock()

    await handle_remember_rule(message, conn)

    message.answer.assert_awaited_once_with("Не понял правило. Напишите: «запомни, <правило>».")


async def test_handle_publish_marks_draft_and_clears_keyboard(monkeypatch):
    callback = MagicMock()
    callback.data = "publish:7"
    callback.message = MagicMock()
    callback.message.edit_reply_markup = AsyncMock()
    callback.answer = AsyncMock()
    conn = MagicMock()

    marked = {}
    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.mark_draft_published",
        lambda c, draft_id: marked.setdefault("id", draft_id),
    )

    await handle_publish(callback, conn)

    assert marked["id"] == 7
    callback.message.edit_reply_markup.assert_awaited_once_with(reply_markup=None)
    callback.answer.assert_awaited_once()
