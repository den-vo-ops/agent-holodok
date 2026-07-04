from holodok_agent.bot.messages import (
    ONBOARDING_MESSAGES,
    HELP_MESSAGE,
    REPORT_STUB_MESSAGE,
    MARKET_STUB_MESSAGE,
)

MENU_LABELS = [
    "✍️ Создать контент",
    "📊 Показать отчёт",
    "🔍 Спросить о рынке",
    "📝 Мои правила",
    "⚙️ Обучить стиль",
    "❓ Помощь",
]


def test_onboarding_has_exactly_three_messages():
    assert len(ONBOARDING_MESSAGES) == 3
    assert all(isinstance(m, str) and m.strip() for m in ONBOARDING_MESSAGES)


def test_second_onboarding_message_explains_settov():
    assert "/settov" in ONBOARDING_MESSAGES[1]
    assert "/done" in ONBOARDING_MESSAGES[1]


def test_help_mentions_commands():
    assert "/settov" in HELP_MESSAGE
    assert "/help" in HELP_MESSAGE


def test_help_explains_every_menu_button():
    for label in MENU_LABELS:
        assert label in HELP_MESSAGE


def test_stub_messages_are_distinct_and_mention_phase():
    assert REPORT_STUB_MESSAGE != MARKET_STUB_MESSAGE
    assert "1C" in REPORT_STUB_MESSAGE or "фаз" in REPORT_STUB_MESSAGE.lower()
    assert "1C" in MARKET_STUB_MESSAGE or "фаз" in MARKET_STUB_MESSAGE.lower()
