# holodok_agent/bot/handlers.py
from datetime import datetime, timezone

from aiogram import F, Router
from aiogram.filters import BaseFilter, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from holodok_agent import db
from holodok_agent.bot.auth import is_owner
from holodok_agent.bot.keyboards import (
    build_regenerate_and_publish_keyboard,
    build_scenario_menu,
    parse_draft_callback,
    parse_scenario_callback,
)
from holodok_agent.llm.content import generate_content
from holodok_agent.llm.errors import LLMError
from holodok_agent.llm.style import analyze_style
from holodok_agent.rules import extract_rule_from_message

ONBOARDING_PROMPT = (
    "Привет! Я — твой личный агент. Чтобы писать в твоём стиле, пришли несколько "
    "старых объявлений или постов (по одному сообщению). Когда закончишь — напиши /done."
)
SCENARIO_MENU_PROMPT = "Выбери, что сделать:"
SCENARIO_INPUT_PROMPTS = {
    "vk_post": "О чём пост? Опиши коротко (например: последний выполненный заказ).",
    "avito_ad": "Что указать в объявлении? Опиши услугу/цену/условия.",
    "review_reply": "Пришли текст отзыва, на который нужно ответить.",
    "idea": "",
}

LAST_GENERATION: dict[int, tuple[str, str]] = {}


class Onboarding(StatesGroup):
    waiting_for_samples = State()


class ScenarioFlow(StatesGroup):
    waiting_for_input = State()


class MetricsFlow(StatesGroup):
    waiting_for_monthly_answer = State()


class IsOwner(BaseFilter):
    def __init__(self, owner_id: int) -> None:
        self.owner_id = owner_id

    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return is_owner(event.from_user.id, self.owner_id)


async def handle_start(message: Message, state: FSMContext, conn) -> None:
    profile = db.get_style_profile(conn)
    if profile is None:
        await state.set_state(Onboarding.waiting_for_samples)
        await state.update_data(samples=[])
        await message.answer(ONBOARDING_PROMPT)
        return
    await message.answer(SCENARIO_MENU_PROMPT, reply_markup=build_scenario_menu())


async def handle_onboarding_sample(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    samples = data.get("samples", [])
    samples.append(message.text)
    await state.update_data(samples=samples)
    await message.answer(f"Принял. Уже {len(samples)} текст(ов). Пришли ещё или напиши /done.")


async def handle_onboarding_done(message: Message, state: FSMContext, conn, claude_client) -> None:
    data = await state.get_data()
    samples = data.get("samples", [])
    if not samples:
        await message.answer("Пришли хотя бы один текст перед /done.")
        return
    try:
        profile = analyze_style(claude_client, samples)
    except LLMError as exc:
        await message.answer(exc.user_message)
        return
    db.save_style_profile(
        conn,
        profile["tone_summary"],
        profile["lexicon_notes"],
        profile["structure_notes"],
        samples,
    )
    await state.clear()
    await message.answer("Стиль запомнил!")
    await message.answer(SCENARIO_MENU_PROMPT, reply_markup=build_scenario_menu())


async def handle_remember_rule(message: Message, conn) -> None:
    rule = extract_rule_from_message(message.text)
    if rule is None:
        await message.answer("Не понял правило. Напишите: «запомни, <правило>».")
        return
    db.add_hard_rule(conn, rule)
    await message.answer(f"Запомнил: {rule}")


async def handle_scenario_selected(callback: CallbackQuery, state: FSMContext, conn, claude_client) -> None:
    scenario = parse_scenario_callback(callback.data)
    if scenario == "idea":
        await _generate_and_send(callback.message, conn, claude_client, scenario, user_input="")
        await callback.answer()
        return
    await state.set_state(ScenarioFlow.waiting_for_input)
    await state.update_data(scenario=scenario)
    await callback.message.answer(SCENARIO_INPUT_PROMPTS[scenario])
    await callback.answer()


async def handle_scenario_input(message: Message, state: FSMContext, conn, claude_client) -> None:
    data = await state.get_data()
    scenario = data["scenario"]
    await state.clear()
    await _generate_and_send(message, conn, claude_client, scenario, message.text)


async def _generate_and_send(message: Message, conn, claude_client, scenario: str, user_input: str) -> None:
    profile = db.get_style_profile(conn)
    if profile is None:
        await message.answer("Сначала пройди обучение стилю: напиши /start.")
        return
    hard_rules = db.get_hard_rules(conn)
    try:
        text = generate_content(claude_client, profile, hard_rules, scenario, user_input)
    except LLMError as exc:
        await message.answer(exc.user_message)
        return
    draft_id = db.record_draft(conn, scenario)
    LAST_GENERATION[draft_id] = (scenario, user_input)
    await message.answer(text, reply_markup=build_regenerate_and_publish_keyboard(draft_id))


async def handle_regenerate(callback: CallbackQuery, conn, claude_client) -> None:
    _, draft_id = parse_draft_callback(callback.data)
    scenario, user_input = LAST_GENERATION.get(draft_id, (None, None))
    if scenario is None:
        await callback.answer("Не нашёл контекст для переделки, начни заново.", show_alert=True)
        return
    await _generate_and_send(callback.message, conn, claude_client, scenario, user_input)
    await callback.answer()


async def handle_publish(callback: CallbackQuery, conn) -> None:
    _, draft_id = parse_draft_callback(callback.data)
    db.mark_draft_published(conn, draft_id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer("Отметил как опубликованное.")


async def handle_monthly_metrics_answer(message: Message, state: FSMContext, conn) -> None:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    db.save_monthly_metrics(conn, month, message.text)
    await state.clear()
    await message.answer("Спасибо, записал.")


def build_router(owner_id: int) -> Router:
    router = Router()
    router.message.filter(IsOwner(owner_id))
    router.callback_query.filter(IsOwner(owner_id))

    router.message.register(handle_remember_rule, F.text.startswith("запомни") | F.text.startswith("Запомни"))
    router.message.register(handle_start, Command("start"))
    router.message.register(
        handle_onboarding_done, Command("done"), StateFilter(Onboarding.waiting_for_samples)
    )
    router.message.register(handle_onboarding_sample, StateFilter(Onboarding.waiting_for_samples))
    router.message.register(handle_scenario_input, StateFilter(ScenarioFlow.waiting_for_input))
    router.message.register(handle_monthly_metrics_answer, StateFilter(MetricsFlow.waiting_for_monthly_answer))

    router.callback_query.register(handle_scenario_selected, F.data.startswith("scenario:"))
    router.callback_query.register(handle_regenerate, F.data.startswith("regen:"))
    router.callback_query.register(handle_publish, F.data.startswith("publish:"))

    return router
