# Главное меню на reply-клавиатуре — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить постоянное главное меню на reply-клавиатуре с 5 кнопками (2 живые, 1 переобучение стиля, 2 заглушки), которое показывается после `/start` при готовом профиле стиля.

**Architecture:** Чистая функция `build_main_menu()` в `keyboards.py` строит `ReplyKeyboardMarkup`; подписи кнопок — именованные константы там же, единый источник правды для клавиатуры и для фильтров хендлеров. Тонкие хендлеры в `handlers.py` реагируют на точный текст кнопок; заглушки отвечают строковой константой. Inline-меню сценариев не меняется — теперь открывается кнопкой «Создать контент».

**Tech Stack:** Python 3.11+, aiogram >=3.4,<4, pytest + pytest-asyncio (`asyncio_mode = auto`).

## Global Constraints

- LLM-провайдер Groq; данная фича LLM не вызывает — только UI и чтение БД.
- Хендлеры тестируются прямым вызовом с `MagicMock`/`AsyncMock`, без поднятия Dispatcher (CLAUDE.md §6).
- Async-тесты без декоратора `@pytest.mark.asyncio` (`asyncio_mode = auto`).
- Новый код без TODO/заглушек-плейсхолдеров в коде (заглушки-ответы кнопок — это осознанная фича, не плейсхолдер).
- Подписи кнопок используются и в клавиатуре, и в фильтрах — только через общие константы, не дублировать строковые литералы.

---

### Task 1: Reply-клавиатура `build_main_menu`

**Files:**
- Modify: `holodok_agent/bot/keyboards.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: ничего нового.
- Produces:
  - Константы `MENU_CREATE_CONTENT`, `MENU_SHOW_REPORT`, `MENU_ASK_MARKET`, `MENU_MY_RULES`, `MENU_RETRAIN_STYLE` (все `str`).
  - `build_main_menu() -> ReplyKeyboardMarkup` — раскладка 3 ряда: `[CREATE, REPORT]`, `[ASK, RULES]`, `[RETRAIN]`; `resize_keyboard=True`, `is_persistent=True`.

- [ ] **Step 1: Write the failing test**

Добавить в `tests/test_keyboards.py`:

```python
def test_build_main_menu_layout_and_flags():
    from holodok_agent.bot.keyboards import (
        build_main_menu,
        MENU_CREATE_CONTENT,
        MENU_SHOW_REPORT,
        MENU_ASK_MARKET,
        MENU_MY_RULES,
        MENU_RETRAIN_STYLE,
    )

    menu = build_main_menu()
    texts = [[btn.text for btn in row] for row in menu.keyboard]

    assert texts == [
        [MENU_CREATE_CONTENT, MENU_SHOW_REPORT],
        [MENU_ASK_MARKET, MENU_MY_RULES],
        [MENU_RETRAIN_STYLE],
    ]
    assert menu.resize_keyboard is True
    assert menu.is_persistent is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_keyboards.py::test_build_main_menu_layout_and_flags -v`
Expected: FAIL с `ImportError: cannot import name 'build_main_menu'`.

- [ ] **Step 3: Write minimal implementation**

В `holodok_agent/bot/keyboards.py` расширить импорт и добавить константы + функцию.

Заменить строку импорта:

```python
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
```

на:

```python
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
```

Добавить в конец файла:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: PASS (новый тест + существующие тесты keyboards зелёные).

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat(bot): add reply main-menu keyboard with 5 buttons"
```

---

### Task 2: Хендлеры кнопок меню + переход на главное меню

**Files:**
- Modify: `holodok_agent/bot/handlers.py`
- Test: `tests/test_handlers.py`

**Interfaces:**
- Consumes из Task 1: `build_main_menu`, `MENU_CREATE_CONTENT`, `MENU_SHOW_REPORT`, `MENU_ASK_MARKET`, `MENU_MY_RULES`, `MENU_RETRAIN_STYLE`.
- Produces:
  - Константы `STUB_MESSAGE`, `MAIN_MENU_PROMPT`, `NO_RULES_MESSAGE` (все `str`).
  - `handle_menu_create_content(message) -> None` — отвечает inline-меню сценариев.
  - `handle_menu_my_rules(message, conn) -> None` — список правил или подсказка.
  - `handle_menu_retrain_style(message, state) -> None` — перезапуск онбординга.
  - `handle_menu_stub(message) -> None` — ответ `STUB_MESSAGE`.
  - `handle_start` и `handle_onboarding_done` теперь показывают `build_main_menu()` вместо `build_scenario_menu()`.
  - Регистрация 4 новых хендлеров в `build_router` **до** `handle_remember_rule` и до state-фильтрованных хендлеров.

- [ ] **Step 1: Write the failing tests**

Добавить в `tests/test_handlers.py`. Сначала расширить импорт из `holodok_agent.bot.handlers`:

```python
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
```

Добавить тесты в конец файла:

```python
async def test_handle_menu_create_content_sends_scenario_menu():
    message = MagicMock()
    message.answer = AsyncMock()

    await handle_menu_create_content(message)

    message.answer.assert_awaited_once()
    _, kwargs = message.answer.call_args
    assert "reply_markup" in kwargs


async def test_handle_menu_my_rules_lists_saved_rules(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.get_hard_rules",
        lambda c: ["не демпинговать", "скидка не больше 10%"],
    )

    await handle_menu_my_rules(message, conn)

    message.answer.assert_awaited_once()
    text = message.answer.call_args.args[0]
    assert "не демпинговать" in text
    assert "скидка не больше 10%" in text


async def test_handle_menu_my_rules_prompts_when_empty(monkeypatch):
    message = MagicMock()
    message.answer = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr("holodok_agent.bot.handlers.db.get_hard_rules", lambda c: [])

    await handle_menu_my_rules(message, conn)

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

    await handle_menu_stub(message)

    message.answer.assert_awaited_once_with(STUB_MESSAGE)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_handlers.py -k "menu" -v`
Expected: FAIL с `ImportError: cannot import name 'handle_menu_create_content'`.

- [ ] **Step 3: Write minimal implementation**

В `holodok_agent/bot/handlers.py`:

(3a) Расширить импорт из keyboards:

```python
from holodok_agent.bot.keyboards import (
    build_main_menu,
    build_regenerate_and_publish_keyboard,
    build_scenario_menu,
    parse_draft_callback,
    parse_scenario_callback,
    MENU_CREATE_CONTENT,
    MENU_SHOW_REPORT,
    MENU_ASK_MARKET,
    MENU_MY_RULES,
    MENU_RETRAIN_STYLE,
)
```

(3b) Добавить константы рядом с `SCENARIO_MENU_PROMPT`:

```python
MAIN_MENU_PROMPT = "Чем помочь? Выбери действие в меню снизу."
NO_RULES_MESSAGE = "Пока нет сохранённых правил. Чтобы добавить, напиши: «запомни, <правило>»."
STUB_MESSAGE = "Эта функция появится после подключения разведки и аналитики (Фаза 1C/1D)."
```

(3c) В `handle_start` заменить показ inline-меню на главное меню. Было:

```python
    await message.answer(SCENARIO_MENU_PROMPT, reply_markup=build_scenario_menu())
```

Стало:

```python
    await message.answer(MAIN_MENU_PROMPT, reply_markup=build_main_menu())
```

(3d) В `handle_onboarding_done` в самом конце заменить строку показа inline-меню. Было:

```python
    await message.answer(SCENARIO_MENU_PROMPT, reply_markup=build_scenario_menu())
```

Стало:

```python
    await message.answer(MAIN_MENU_PROMPT, reply_markup=build_main_menu())
```

(3e) Добавить 4 хендлера (например, после `handle_remember_rule`):

```python
async def handle_menu_create_content(message: Message) -> None:
    await message.answer(SCENARIO_MENU_PROMPT, reply_markup=build_scenario_menu())


async def handle_menu_my_rules(message: Message, conn) -> None:
    rules = db.get_hard_rules(conn)
    if not rules:
        await message.answer(NO_RULES_MESSAGE)
        return
    listed = "\n".join(f"{i}. {rule}" for i, rule in enumerate(rules, 1))
    await message.answer(
        f"Твои правила:\n{listed}\n\nЧтобы добавить ещё — напиши: «запомни, <правило>»."
    )


async def handle_menu_retrain_style(message: Message, state: FSMContext) -> None:
    await state.set_state(Onboarding.waiting_for_samples)
    await state.update_data(samples=[])
    await message.answer(ONBOARDING_PROMPT)


async def handle_menu_stub(message: Message) -> None:
    await message.answer(STUB_MESSAGE)
```

(3f) В `build_router` зарегистрировать кнопки **первыми среди message-хендлеров** (до `handle_remember_rule`), чтобы нажатие кнопки не перехватывалось правилом «запомни…» и state-фильтрованными хендлерами (даёт «аварийный выход» из незавершённого сценария). Вставить сразу после строк с `router.callback_query.filter(...)` / перед `router.message.register(handle_remember_rule, ...)`:

```python
    router.message.register(handle_menu_create_content, F.text == MENU_CREATE_CONTENT)
    router.message.register(handle_menu_my_rules, F.text == MENU_MY_RULES)
    router.message.register(handle_menu_retrain_style, F.text == MENU_RETRAIN_STYLE)
    router.message.register(handle_menu_stub, F.text.in_({MENU_SHOW_REPORT, MENU_ASK_MARKET}))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: PASS. В частности существующий `test_handle_start_shows_menu_when_style_profile_exists` остаётся зелёным (`reply_markup` по-прежнему передаётся, теперь это `build_main_menu()`).

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: всё зелёное (было 61 тест + новые из Task 1 и Task 2).

- [ ] **Step 6: Commit**

```bash
git add holodok_agent/bot/handlers.py tests/test_handlers.py
git commit -m "feat(bot): wire reply main-menu buttons and open it after /start"
```

- [ ] **Step 7: Ручной smoke-тест (aiogram wiring, вне unit-покрытия)**

Локально с реальным ботом (CLAUDE.md §8): `/start` → появляется reply-клавиатура из 5 кнопок. Проверить: «Создать контент» открывает inline-сценарии; «Мои правила» показывает список/подсказку; «Обучить стиль» просит прислать образцы; «Показать отчёт» и «Спросить о рынке» отвечают `STUB_MESSAGE`; нажатие кнопки во время сценария выходит из него в меню.

---

## Заметки по обновлению документации (после исполнения)

- `CLAUDE.md` §2: отметить наличие главного меню в `keyboards.py`/`handlers.py`, если структура описывается детальнее.
- `Plan.md`: отметить фичу «главное меню» как выполненную в соответствующей фазе.
- `spec.md` §6 п.2: путь UX теперь «мастер видит главное меню → выбирает роль» — синхронизировать при следующем раунде `discovery-interview`, не задним числом здесь.
