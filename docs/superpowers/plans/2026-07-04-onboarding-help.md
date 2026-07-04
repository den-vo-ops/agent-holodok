# Onboarding & Help Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Показать новому пользователю понятный онбординг из 3 сообщений при первом `/start`, добавить команды `/settov` и `/help` (+ кнопку «Помощь»), и понятные мини-подсказки на каждой кнопке.

**Architecture:** Тексты выносятся в новый чистый модуль `bot/messages.py` (юнит-тестируемые константы). Факт «пользователь уже видел онбординг» хранится в новой таблице `onboarded_users`. Хендлеры остаются тонким связующим слоем, `/start` переключается с гейта «есть профиль стиля» на гейт «онбордился ли пользователь».

**Tech Stack:** Python 3.11+, aiogram 3.x, SQLite (stdlib), pytest + pytest-asyncio (`asyncio_mode = auto`).

## Global Constraints

- Все пользовательские тексты — на русском, тон на «ты» (как в текущих хендлерах).
- Тесты зеркалят модули один-в-один; async-тесты без `@pytest.mark.asyncio`.
- Хендлеры тестируются прямым вызовом с `MagicMock`/`AsyncMock`, без Dispatcher.
- Каждая задача заканчивается зелёным `python -m pytest` и коммитом.
- Ровно 3 сообщения онбординга. Онбординг — только новым (не онбордившимся) пользователям.
- Метки кнопок меню — единый источник в `bot/keyboards.py` (`MENU_*`).

---

### Task 1: Таблица onboarded_users и функции доступа

**Files:**
- Modify: `holodok_agent/db.py` (SCHEMA + 2 функции)
- Test: `tests/test_db.py`

**Interfaces:**
- Produces:
  - `has_onboarded(conn, user_id: int) -> bool`
  - `mark_onboarded(conn, user_id: int) -> None` (идемпотентна)

- [ ] **Step 1: Write the failing tests**

Добавить в конец `tests/test_db.py` (и в импорт сверху добавить `has_onboarded, mark_onboarded`):

```python
def test_has_onboarded_false_for_unknown_user(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    assert has_onboarded(conn, 111) is False


def test_mark_onboarded_makes_user_known(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    mark_onboarded(conn, 111)
    assert has_onboarded(conn, 111) is True


def test_mark_onboarded_is_idempotent(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    mark_onboarded(conn, 111)
    mark_onboarded(conn, 111)  # не должно падать
    assert has_onboarded(conn, 111) is True


def test_mark_onboarded_scoped_per_user(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    mark_onboarded(conn, 111)
    assert has_onboarded(conn, 222) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -k onboarded -v`
Expected: FAIL (ImportError: cannot import name `has_onboarded`).

- [ ] **Step 3: Implement in `holodok_agent/db.py`**

В `SCHEMA` добавить (внутри тройных кавычек, после `metrics_monthly`):

```sql

CREATE TABLE IF NOT EXISTS onboarded_users (
    user_id INTEGER PRIMARY KEY,
    first_seen_at TEXT NOT NULL
);
```

В конец файла добавить:

```python
def has_onboarded(conn, user_id: int) -> bool:
    row = conn.execute(
        "SELECT 1 FROM onboarded_users WHERE user_id = ?", (user_id,)
    ).fetchone()
    return row is not None


def mark_onboarded(conn, user_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO onboarded_users (user_id, first_seen_at) VALUES (?, ?)",
        (user_id, _now()),
    )
    conn.commit()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: PASS (все, включая старые).

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/db.py tests/test_db.py
git commit -m "feat(db): track onboarded users"
```

---

### Task 2: Модуль текстов bot/messages.py

**Files:**
- Create: `holodok_agent/bot/messages.py`
- Test: `tests/test_messages.py`

**Interfaces:**
- Consumes: `MENU_CREATE_CONTENT, MENU_SHOW_REPORT, MENU_ASK_MARKET, MENU_MY_RULES, MENU_RETRAIN_STYLE, MENU_HELP` из `bot/keyboards.py` — **используются только внутри тестов**; в `messages.py` метки вписаны в текст строками (чтобы не создавать импорт-цикл keyboards↔messages).
- Produces:
  - `ONBOARDING_MESSAGES: list[str]` (len == 3)
  - `HELP_MESSAGE: str`
  - `REPORT_STUB_MESSAGE: str`
  - `MARKET_STUB_MESSAGE: str`

> Примечание: `MENU_HELP` создаётся в Task 3. Эта задача не импортирует его в рантайме — только тест ссылается на строковые метки. Тест Task 2 использует литералы меток, а не импорт, чтобы задачи были независимы.

- [ ] **Step 1: Write the failing tests**

Создать `tests/test_messages.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_messages.py -v`
Expected: FAIL (ModuleNotFoundError: `holodok_agent.bot.messages`).

- [ ] **Step 3: Implement `holodok_agent/bot/messages.py`**

```python
# holodok_agent/bot/messages.py
"""Пользовательские тексты онбординга и справки. Чистые константы — тестируются юнит-тестами."""

ONBOARDING_MESSAGES: list[str] = [
    (
        "👋 Привет! Я — твой личный помощник по контенту.\n\n"
        "Что я умею:\n"
        "✍️ Пишу посты для ВК/Telegram, объявления для Авито/Юлы и ответы на отзывы — в твоём стиле.\n"
        "📝 Запоминаю твои правила (например: «запомни, всегда указывай гарантию 1 год»).\n"
        "📊 Готовлю аналитику по конкурентам и лидам (скоро).\n\n"
        "Главное — я подстраиваюсь под твою манеру писать, чтобы тексты звучали как твои, "
        "а не шаблонные."
    ),
    (
        "Чтобы я писал именно твоим голосом, покажи мне примеры своих текстов.\n\n"
        "Отправь команду /settov и пришли 3–5 своих старых объявлений или постов "
        "(по одному сообщению). Когда закончишь — напиши /done.\n\n"
        "Я разберу твой тон, лексику и структуру и буду держать их в каждом тексте. "
        "Захочешь обновить стиль позже — снова /settov или кнопка «⚙️ Обучить стиль»."
    ),
    (
        "🚀 Быстрый старт:\n"
        "1. /settov — загрузи свой стиль (3–5 текстов, потом /done).\n"
        "2. Кнопка «✍️ Создать контент» — выбери пост / объявление / ответ на отзыв.\n"
        "3. Проверь черновик → «Переделай» или «Опубликовал».\n\n"
        "Кнопки меню всегда внизу экрана. Забыл, что к чему? Жми «❓ Помощь» или /help.\n\n"
        "Погнали! 👇"
    ),
]

HELP_MESSAGE: str = (
    "❓ Как пользоваться ботом\n\n"
    "Команды:\n"
    "• /settov — загрузить/обновить твой стиль (пришли 3–5 текстов, потом /done).\n"
    "• /help — показать эту инструкцию.\n"
    "• «запомни, …» — сохранить правило (напр. «запомни, всегда пиши телефон в конце»).\n\n"
    "Кнопки меню:\n"
    "✍️ Создать контент — выбрать формат (пост ВК/Telegram, объявление Авито/Юла, "
    "ответ на отзыв, «дай идею») и получить черновик в твоём стиле.\n"
    "📊 Показать отчёт — еженедельная сводка по конкурентам и лидам (появится в следующей фазе).\n"
    "🔍 Спросить о рынке — быстрый вопрос про цены и спрос (появится в следующей фазе).\n"
    "📝 Мои правила — список правил, которые я всегда учитываю.\n"
    "⚙️ Обучить стиль — то же, что /settov.\n"
    "❓ Помощь — эта инструкция.\n\n"
    "Под черновиком: «Переделай» — сгенерировать заново, «Опубликовал» — отметить, "
    "что выложил (для статистики)."
)

REPORT_STUB_MESSAGE: str = (
    "📊 Здесь будет еженедельная сводка по конкурентам и горячим лидам. "
    "Появится после подключения разведки и аналитики (Фаза 1C/1D)."
)

MARKET_STUB_MESSAGE: str = (
    "🔍 Здесь можно будет быстро спросить про цены и спрос по рынку Симферополя. "
    "Появится после подключения разведки (Фаза 1C/1D)."
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_messages.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/messages.py tests/test_messages.py
git commit -m "feat(bot): add onboarding & help texts module"
```

---

### Task 3: Кнопка «Помощь» в клавиатуре

**Files:**
- Modify: `holodok_agent/bot/keyboards.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Produces: `MENU_HELP: str = "❓ Помощь"`; `build_main_menu()` содержит 6 кнопок, включая `MENU_HELP`.

- [ ] **Step 1: Write the failing test**

Добавить в `tests/test_keyboards.py` (импортировать `build_main_menu, MENU_HELP` при необходимости):

```python
def test_main_menu_contains_help_button():
    from holodok_agent.bot.keyboards import build_main_menu, MENU_HELP

    markup = build_main_menu()
    labels = [btn.text for row in markup.keyboard for btn in row]
    assert MENU_HELP in labels
    assert MENU_HELP == "❓ Помощь"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_keyboards.py::test_main_menu_contains_help_button -v`
Expected: FAIL (ImportError: `MENU_HELP`).

- [ ] **Step 3: Implement in `holodok_agent/bot/keyboards.py`**

После строки `MENU_RETRAIN_STYLE = "⚙️ Обучить стиль"` добавить:

```python
MENU_HELP = "❓ Помощь"
```

Заменить тело `build_main_menu()` на раскладку с 6 кнопками:

```python
def build_main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=MENU_CREATE_CONTENT), KeyboardButton(text=MENU_SHOW_REPORT)],
            [KeyboardButton(text=MENU_ASK_MARKET), KeyboardButton(text=MENU_MY_RULES)],
            [KeyboardButton(text=MENU_RETRAIN_STYLE), KeyboardButton(text=MENU_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat(bot): add Help button to main menu"
```

---

### Task 4: Онбординг-гейт в /start + команды /settov, /help + разнесённые заглушки

**Files:**
- Modify: `holodok_agent/bot/handlers.py`
- Test: `tests/test_handlers.py`

**Interfaces:**
- Consumes: `db.has_onboarded`, `db.mark_onboarded` (Task 1); `ONBOARDING_MESSAGES, HELP_MESSAGE, REPORT_STUB_MESSAGE, MARKET_STUB_MESSAGE` (Task 2); `MENU_HELP` (Task 3).
- Produces (сигнатуры для Task 5 — регистрация роутера):
  - `handle_start(message, state, conn)` — новый: онбординг-гейт
  - `handle_settov(message, state)` — запуск загрузки стиля (заменяет `handle_menu_retrain_style`)
  - `handle_help(message, state)` — показывает `HELP_MESSAGE`, чистит стейт
  - `handle_menu_report_stub(message, state)` / `handle_menu_market_stub(message, state)` — заменяют `handle_menu_stub`

- [ ] **Step 1: Write the failing tests**

В `tests/test_handlers.py` — обновить импорт-блок сверху: убрать `handle_menu_retrain_style, handle_menu_stub, STUB_MESSAGE`, добавить `handle_settov, handle_help, handle_menu_report_stub, handle_menu_market_stub`. Также добавить импорты текстов:

```python
from holodok_agent.bot.messages import (
    ONBOARDING_MESSAGES,
    HELP_MESSAGE,
    REPORT_STUB_MESSAGE,
    MARKET_STUB_MESSAGE,
)
```

Заменить два теста `test_handle_start_*` на новые (гейт теперь по `has_onboarded`, а `message.from_user.id` задаётся явно):

```python
async def test_handle_start_new_user_shows_onboarding_then_menu(monkeypatch):
    message = MagicMock()
    message.from_user.id = 111
    message.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr("holodok_agent.bot.handlers.db.has_onboarded", lambda c, uid: False)
    marked = {}
    monkeypatch.setattr(
        "holodok_agent.bot.handlers.db.mark_onboarded",
        lambda c, uid: marked.setdefault("uid", uid),
    )

    await handle_start(message, state, conn)

    # 3 сообщения онбординга + итоговое меню
    assert message.answer.await_count == len(ONBOARDING_MESSAGES) + 1
    sent = [call.args[0] for call in message.answer.call_args_list]
    assert sent[:3] == ONBOARDING_MESSAGES
    # последнее сообщение — с клавиатурой меню
    assert "reply_markup" in message.answer.call_args_list[-1].kwargs
    # пользователь помечен как онбордившийся, в загрузку образцов НЕ входим
    assert marked["uid"] == 111
    state.set_state.assert_not_called()


async def test_handle_start_known_user_shows_menu_only(monkeypatch):
    message = MagicMock()
    message.from_user.id = 111
    message.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()
    conn = MagicMock()

    monkeypatch.setattr("holodok_agent.bot.handlers.db.has_onboarded", lambda c, uid: True)
    monkeypatch.setattr("holodok_agent.bot.handlers.db.mark_onboarded", lambda c, uid: None)

    await handle_start(message, state, conn)

    message.answer.assert_awaited_once()
    assert "reply_markup" in message.answer.call_args.kwargs
    state.set_state.assert_not_called()
```

Заменить `test_handle_menu_retrain_style_restarts_onboarding` на:

```python
async def test_handle_settov_starts_style_upload():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.set_state = AsyncMock()
    state.update_data = AsyncMock()

    await handle_settov(message, state)

    state.set_state.assert_awaited_once_with(Onboarding.waiting_for_samples)
    state.update_data.assert_awaited_once_with(samples=[])
    message.answer.assert_awaited_once()
```

Заменить `test_handle_menu_stub_replies_with_stub_message` на два теста и добавить тест help:

```python
async def test_handle_menu_report_stub_explains_feature():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await handle_menu_report_stub(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once_with(REPORT_STUB_MESSAGE)


async def test_handle_menu_market_stub_explains_feature():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await handle_menu_market_stub(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once_with(MARKET_STUB_MESSAGE)


async def test_handle_help_shows_help_and_clears_state():
    message = MagicMock()
    message.answer = AsyncMock()
    state = MagicMock()
    state.clear = AsyncMock()

    await handle_help(message, state)

    state.clear.assert_awaited_once()
    message.answer.assert_awaited_once_with(HELP_MESSAGE)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: FAIL (ImportError на новых именах / старые имена удалены).

- [ ] **Step 3: Implement in `holodok_agent/bot/handlers.py`**

3a. Обновить импорты сверху:

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
    MENU_HELP,
)
from holodok_agent.bot.messages import (
    ONBOARDING_MESSAGES,
    HELP_MESSAGE,
    REPORT_STUB_MESSAGE,
    MARKET_STUB_MESSAGE,
)
```

3b. Удалить константу `STUB_MESSAGE`. Обновить гейт-сообщение в `_generate_and_send`: заменить строку
`await message.answer("Сначала пройди обучение стилю: напиши /start.")`
на
`await message.answer("Сначала загрузи свой стиль — команда /settov (или кнопка «⚙️ Обучить стиль»).")`

3c. Переписать `handle_start`:

```python
async def handle_start(message: Message, state: FSMContext, conn) -> None:
    if not db.has_onboarded(conn, message.from_user.id):
        for text in ONBOARDING_MESSAGES:
            await message.answer(text)
        db.mark_onboarded(conn, message.from_user.id)
    await message.answer(MAIN_MENU_PROMPT, reply_markup=build_main_menu())
```

3d. Заменить `handle_menu_retrain_style` на `handle_settov` (та же логика, новое имя):

```python
async def handle_settov(message: Message, state: FSMContext) -> None:
    await state.set_state(Onboarding.waiting_for_samples)
    await state.update_data(samples=[])
    await message.answer(ONBOARDING_PROMPT)
```

3e. Добавить `handle_help`:

```python
async def handle_help(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(HELP_MESSAGE)
```

3f. Заменить `handle_menu_stub` на два хендлера:

```python
async def handle_menu_report_stub(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(REPORT_STUB_MESSAGE)


async def handle_menu_market_stub(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(MARKET_STUB_MESSAGE)
```

3g. Мини-подсказка «Создать контент»: изменить константу
`SCENARIO_MENU_PROMPT = "Выбери, что сделать:"`
на
`SCENARIO_MENU_PROMPT = "✍️ Соберу черновик в твоём стиле. Выбери формат:"`

3h. Мини-подсказка «Мои правила»: в `handle_menu_my_rules` заменить строку формирования ответа так, чтобы перед списком шёл вводный текст (список правил остаётся):

```python
    listed = "\n".join(f"{i}. {rule}" for i, rule in enumerate(rules, 1))
    await message.answer(
        "📝 Это правила, которые я всегда держу в голове при генерации.\n\n"
        f"Твои правила:\n{listed}\n\nЧтобы добавить ещё — напиши: «запомни, <правило>»."
    )
```

- [ ] **Step 4: Обновить регистрацию в `build_router`**

Внутри `build_router` заменить блок регистрации `message`-хендлеров так:

```python
    router.message.register(handle_menu_create_content, F.text == MENU_CREATE_CONTENT)
    router.message.register(handle_menu_my_rules, F.text == MENU_MY_RULES)
    router.message.register(handle_settov, F.text == MENU_RETRAIN_STYLE)
    router.message.register(handle_menu_report_stub, F.text == MENU_SHOW_REPORT)
    router.message.register(handle_menu_market_stub, F.text == MENU_ASK_MARKET)
    router.message.register(handle_help, F.text == MENU_HELP)

    router.message.register(handle_remember_rule, F.text.startswith("запомни") | F.text.startswith("Запомни"))
    router.message.register(handle_start, Command("start"))
    router.message.register(handle_settov, Command("settov"))
    router.message.register(handle_help, Command("help"))
    router.message.register(
        handle_onboarding_done, Command("done"), StateFilter(Onboarding.waiting_for_samples)
    )
    router.message.register(handle_onboarding_sample, StateFilter(Onboarding.waiting_for_samples))
    router.message.register(handle_scenario_input, StateFilter(ScenarioFlow.waiting_for_input))
    router.message.register(handle_monthly_metrics_answer, StateFilter(MetricsFlow.waiting_for_monthly_answer))
```

> Порядок важен: `Command("settov")`/`Command("help")` и кнопочные регистрации стоят до общих `StateFilter`-хендлеров, чтобы команда прерывала активный поток (консистентно с уже принятым поведением кнопок меню).

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest -v`
Expected: PASS (весь набор, включая старые тесты хендлеров).

- [ ] **Step 6: Commit**

```bash
git add holodok_agent/bot/handlers.py tests/test_handlers.py
git commit -m "feat(bot): onboarding gate on /start, /settov, /help, per-button hints"
```

---

### Task 5: Регистрация команд в меню Telegram

**Files:**
- Modify: `holodok_agent/bot/main.py`
- Test: `tests/test_main.py` (создать)

**Interfaces:**
- Consumes: aiogram `Bot.set_my_commands`.
- Produces: `build_bot_commands() -> list[BotCommand]` — чистая функция, вызывается в `run()`.

- [ ] **Step 1: Write the failing test**

Создать `tests/test_main.py`:

```python
from holodok_agent.bot.main import build_bot_commands


def test_bot_commands_cover_start_settov_help():
    commands = {c.command: c.description for c in build_bot_commands()}
    assert set(commands) == {"start", "settov", "help"}
    assert all(desc.strip() for desc in commands.values())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_main.py -v`
Expected: FAIL (ImportError: `build_bot_commands`).

- [ ] **Step 3: Implement in `holodok_agent/bot/main.py`**

Добавить импорт `from aiogram.types import BotCommand, ErrorEvent` (расширить существующий импорт `ErrorEvent`). Добавить функцию:

```python
def build_bot_commands() -> list[BotCommand]:
    return [
        BotCommand(command="start", description="Запустить бота / открыть меню"),
        BotCommand(command="settov", description="Загрузить свой стиль (тон-оф-войс)"),
        BotCommand(command="help", description="Как пользоваться ботом"),
    ]
```

В `run()` после создания `bot` и до `start_polling` добавить:

```python
    await bot.set_my_commands(build_bot_commands())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/main.py tests/test_main.py
git commit -m "feat(bot): register /start /settov /help in Telegram command menu"
```

---

### Task 6: Обновление документации

**Files:**
- Modify: `CLAUDE.md` (§2 структура — добавить `bot/messages.py`; §8 если нужно), `Plan.md` (отметить фичу онбординга/справки)

**Interfaces:** нет кода.

- [ ] **Step 1: Обновить `CLAUDE.md`**

В §2 в дерево `holodok_agent/bot/` добавить строку:
`│       ├── messages.py                # тексты онбординга и справки (чистые константы)`
Обновить описание `handlers.py`: упомянуть онбординг-гейт по `onboarded_users`, команды `/settov`, `/help`.

- [ ] **Step 2: Обновить `Plan.md`**

Добавить в трекер прогресса запись о завершённой фиче «Онбординг + справка (/settov, /help, мини-подсказки)» со статусом «сделано, тесты зелёные».

- [ ] **Step 3: Run full test suite (sanity)**

Run: `python -m pytest -v`
Expected: PASS (без изменений — правки только в docs).

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md Plan.md
git commit -m "docs: record onboarding & help feature"
```

---

## Ручной smoke-тест (после всех задач)

Сетевые вызовы Telegram юнит-тестами не покрываются — проверить вручную (см. CLAUDE.md §6):

1. Удалить/переименовать локальную БД (или новый `user_id`) → `/start` показывает 3 сообщения онбординга, затем меню.
2. Повторный `/start` → только меню, без 3 сообщений.
3. `/settov` → просит прислать образцы; после /done — «Стиль запомнил!» + меню.
4. `/help` и кнопка «❓ Помощь» → полная инструкция.
5. Кнопки «📊 Показать отчёт» и «🔍 Спросить о рынке» → разные понятные пояснения.
6. Синее меню команд Telegram содержит /start, /settov, /help.

## Self-Review

- **Spec coverage:** первый/повторный `/start` (Task 4) ✓; `/settov` (Task 4) ✓; `/help` + кнопка (Task 3+4) ✓; мини-подсказки + разнесённые заглушки (Task 4) ✓; таблица onboarded_users (Task 1) ✓; модуль текстов (Task 2) ✓; set_my_commands (Task 5) ✓; обновление гейт-сообщения генерации (Task 4, 3b) ✓; docs (Task 6) ✓.
- **Placeholder scan:** плейсхолдеров нет — весь код приведён.
- **Type consistency:** `has_onboarded/mark_onboarded(conn, user_id)` совпадают между Task 1 и Task 4; имена хендлеров (`handle_settov`, `handle_help`, `handle_menu_report_stub`, `handle_menu_market_stub`) совпадают между Task 4 определением и регистрацией; `MENU_HELP` определён в Task 3, используется в Task 4; тексты из Task 2 импортируются в Task 4.
