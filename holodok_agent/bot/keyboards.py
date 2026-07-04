# holodok_agent/bot/keyboards.py
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

_SCENARIO_BUTTONS = [
    ("vk_post", "Пост для ВК/Telegram"),
    ("avito_ad", "Объявление Авито/Юла"),
    ("review_reply", "Ответ на отзыв"),
    ("idea", "Дай идею"),
]


def build_scenario_menu() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"scenario:{key}")]
        for key, label in _SCENARIO_BUTTONS
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_scenario_callback(data: str) -> str:
    prefix = "scenario:"
    if not data.startswith(prefix):
        raise ValueError(f"Не сценарный callback: {data}")
    return data[len(prefix):]


def build_regenerate_and_publish_keyboard(draft_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="Переделай", callback_data=f"regen:{draft_id}"),
            InlineKeyboardButton(text="Опубликовал", callback_data=f"publish:{draft_id}"),
        ]]
    )


def parse_draft_callback(data: str) -> tuple[str, int]:
    action, _, raw_id = data.partition(":")
    if action not in {"regen", "publish"} or not raw_id.isdigit():
        raise ValueError(f"Некорректный callback: {data}")
    return action, int(raw_id)


MENU_CREATE_CONTENT = "✍️ Создать контент"
MENU_SHOW_REPORT = "📊 Показать отчёт"
MENU_ASK_MARKET = "🔍 Спросить о рынке"
MENU_MY_RULES = "📝 Мои правила"
MENU_RETRAIN_STYLE = "⚙️ Обучить стиль"


def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_CREATE_CONTENT), KeyboardButton(text=MENU_SHOW_REPORT)],
            [KeyboardButton(text=MENU_ASK_MARKET), KeyboardButton(text=MENU_MY_RULES)],
            [KeyboardButton(text=MENU_RETRAIN_STYLE)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
