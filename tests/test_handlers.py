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
    _generate_and_send,
    handle_menu_create_content,
    handle_menu_my_rules,
    handle_menu_retrain_style,
    handle_menu_stub,
    STUB_MESSAGE,
    NO_RULES_MESSAGE,
)
from holodok_agent.llm.errors import LLMError


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
    llm_client = MagicMock()

    await handle_onboarding_done(message, state, conn, llm_client)

    message.answer.assert_awaited_once_with("Пришли хотя бы один текст перед /done.")


async def test_handle_onboarding_done_saves_profile_and_clears_state(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"samples": ["текст 1"]})
    state.clear = AsyncMock()
    conn = MagicMock()
    llm_client = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.analyze_style",
        lambda client, samples: {"tone_summary": "t", "lexicon_notes": "l", "structure_notes": "s"},
    )
    saved = {}
    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.save_style_profile",
        lambda c, tone, lex, struct, samples: saved.update(tone=tone, samples=samples),
    )

    await handle_onboarding_done(message, state, conn, llm_client)

    state.clear.assert_awaited_once()
    assert saved == {"tone": "t", "samples": ["текст 1"]}
    assert message.answer.await_count == 2


async def test_handle_onboarding_done_shows_user_message_on_llm_error_and_keeps_state(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.get_data = AsyncMock(return_value={"samples": ["текст 1"]})
    state.clear = AsyncMock()
    conn = MagicMock()
    llm_client = MagicMock()

    def _raise(client, samples):
        raise LLMError("boom", user_message="ИИ временно недоступен. Попробуйте ещё раз чуть позже.")

    monkeypatch.setattr("holodok_agent.bot.handlers.analyze_style", _raise)
    save_called = MagicMock()
    monkeypatch.setattr("holodok_agent.bot.handlers.db.save_style_profile", save_called)

    await handle_onboarding_done(message, state, conn, llm_client)

    message.answer.assert_awaited_once_with("ИИ временно недоступен. Попробуйте ещё раз чуть позже.")
    state.clear.assert_not_called()
    save_called.assert_not_called()


async def test_generate_and_send_shows_user_message_on_llm_error_and_skips_draft(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    conn = MagicMock()
    llm_client = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.get_style_profile",
        lambda c: {"tone_summary": "t", "lexicon_notes": "l", "structure_notes": "s"},
    )
    monkeypatch.setattr("holodok_agent.bot.handlers.db.get_hard_rules", lambda c: [])

    def _raise(client, profile, hard_rules, scenario, user_input):
        raise LLMError("boom", user_message="Слишком много запросов к ИИ подряд. Подождите минуту и попробуйте снова.")

    monkeypatch.setattr("holodok_agent.bot.handlers.generate_content", _raise)
    record_draft_called = MagicMock()
    monkeypatch.setattr("holodok_agent.bot.handlers.db.record_draft", record_draft_called)

    await _generate_and_send(message, conn, llm_client, "vk_post", "входные данные")

    message.answer.assert_awaited_once_with(
        "Слишком много запросов к ИИ подряд. Подождите минуту и попробуйте снова."
    )
    record_draft_called.assert_not_called()


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


async def test_handle_menu_create_content_sends_scenario_menu():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await handle_menu_create_content(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    _, kwargs = message.answer.call_args
    assert "reply_markup" in kwargs


async def test_handle_menu_my_rules_lists_saved_rules(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.get_hard_rules",
        lambda c: ["не демпинговать", "скидка не больше 10%"],
    )

    await handle_menu_my_rules(message, state, conn)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "не демпинговать" in text
    assert "скидка не больше 10%" in text


async def test_handle_menu_my_rules_prompts_when_empty(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr("holodok_agent.bot.handlers.db.get_hard_rules", lambda c: [])

    await handle_menu_my_rules(message, state, conn)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once_with(NO_RULES_MESSAGE)


async def test_handle_menu_retrain_style_restarts_onboarding():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    await handle_menu_retrain_style(message, state)

    state.set_state.assert_awaited_once_with(Onboarding.waiting_for_samples)
    state.update_data.assert_awaited_once_with(samples=[])
    message.answer.assert_awaited_once()


async def test_handle_menu_stub_replies_with_stub_message():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await handle_menu_stub(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once_with(STUB_MESSAGE)
