# Holodok Agent — Core (бот, память, стиль, контент) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Построить рабочий скелет Telegram-бота из [spec.md](../../../spec.md): whitelist-доступ, обучение стилю мастера на старых текстах, генерация контента по кнопкам-сценариям, память жёстких правил, учёт использованных черновиков и ежемесячный опрос по метрикам успеха.

**Architecture:** Один Python-процесс на существующем VPS. `aiogram` 3.x как Telegram-фреймворк (async, FSM для многошаговых диалогов онбординга/сценариев). SQLite — единственное хранилище (один пользователь, низкая нагрузка). Отдельный тонкий клиент над Anthropic SDK инкапсулирует все вызовы Claude; вся бизнес-логика (анализ стиля, сборка промптов, парсинг команд) вынесена в чистые функции без побочных эффектов aiogram/Telegram — это то, что действительно тестируется юнит-тестами. Хендлеры aiogram — тонкий связующий слой поверх этих функций.

**Tech Stack:** Python 3.11+, aiogram >=3.4,<4, anthropic >=0.34,<1, apscheduler >=3.10,<4, python-dotenv, pytest + pytest-asyncio.

## Global Constraints

- Единственный пользователь — доступ только по whitelist Telegram ID владельца (spec.md §8).
- Модель Claude — Opus, ID из конфига по умолчанию `claude-opus-4-8` (spec.md, запрос пользователя «разрабатывать будет Opus»).
- Никакой автопубликации контента — бот только готовит черновики (spec.md §5, «явно вне скоупа»).
- Автоматического мониторинга собственной репутации мастера нет — функция «ответ на отзыв» работает только по вручную вставленному тексту (spec.md §5, §10).
- Жёсткие правила стиля не заданы заранее — агент должен уметь запомнить правило, сформулированное мастером в чате, командой вида «запомни, …» (spec.md §5).
- Все тексты, которые пишет бот, и все диалоговые сообщения — на русском языке.
- Бюджет эксплуатации ограничен (~2000–3000₽/мес суммарно на LLM+хостинг) — не вводить платных внешних сервисов сверх Anthropic API без явного решения владельца (spec.md §10).

## Scope of this plan

Этот план покрывает **только** ядро агента: доступ, обучение стилю, генерацию контента по кнопкам, память жёстких правил, учёт черновиков и метрики. **Не входит** (будет отдельными планами):
- Разведка конкурентов на Авито/Юле и еженедельные отчёты — отдельный план, требует захвата и проверки реальной разметки страниц (главный технический риск, spec.md §10.3).
- Горячие лиды (мониторинг локальных чатов) — заблокировано на Фазе 0 (spec.md §9): нет подтверждённых групп и доступа к ним.
- Фазы 2–3 (отзывы конкурентов, соцсети конкурентов).

---

### Task 1: Project scaffolding

**Files:**
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `holodok_agent/__init__.py`
- Create: `holodok_agent/llm/__init__.py`
- Create: `holodok_agent/bot/__init__.py`
- Create: `tests/__init__.py`
- Create: `.env.example`
- Create: `.gitignore`

**Interfaces:**
- Produces: package skeleton that all later tasks import from (`holodok_agent`, `holodok_agent.llm`, `holodok_agent.bot`).

- [ ] **Step 1: Create directory structure and empty package files**

```bash
mkdir -p holodok_agent/llm holodok_agent/bot tests
touch holodok_agent/__init__.py holodok_agent/llm/__init__.py holodok_agent/bot/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write `requirements.txt`**

```
aiogram>=3.4,<4
anthropic>=0.34,<1
apscheduler>=3.10,<4
python-dotenv>=1.0,<2
pytest>=8.0,<9
pytest-asyncio>=0.23,<1
```

- [ ] **Step 3: Write `pytest.ini`**

```ini
[pytest]
testpaths = tests
pythonpath = .
asyncio_mode = auto
```

- [ ] **Step 4: Write `.env.example`**

```
TELEGRAM_BOT_TOKEN=
OWNER_TELEGRAM_ID=
ANTHROPIC_API_KEY=
ANTHROPIC_MODEL=claude-opus-4-8
DB_PATH=holodok_agent.db
```

- [ ] **Step 5: Write `.gitignore`**

```
.venv/
__pycache__/
*.pyc
.env
holodok_agent.db
```

- [ ] **Step 6: Install dependencies and verify pytest runs**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest
```

Expected: pytest exits with "no tests ran" (exit code 5) — no test files exist yet.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt pytest.ini .env.example .gitignore holodok_agent tests
git commit -m "chore: scaffold holodok_agent package structure"
```

---

### Task 2: Config loader

**Files:**
- Create: `holodok_agent/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: environment variables `TELEGRAM_BOT_TOKEN`, `OWNER_TELEGRAM_ID`, `ANTHROPIC_API_KEY`, `ANTHROPIC_MODEL`, `DB_PATH`.
- Produces: `load_config() -> Config`, where `Config` is a frozen dataclass with fields `telegram_bot_token: str`, `owner_telegram_id: int`, `anthropic_api_key: str`, `anthropic_model: str`, `db_path: str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_config.py
import pytest

from holodok_agent.config import load_config


def test_load_config_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
        load_config()


def test_load_config_reads_all_values_with_default_model(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "12345")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)

    config = load_config()

    assert config.telegram_bot_token == "test-token"
    assert config.owner_telegram_id == 12345
    assert config.anthropic_api_key == "test-key"
    assert config.anthropic_model == "claude-opus-4-8"
    assert config.db_path == "holodok_agent.db"


def test_load_config_respects_overrides(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("OWNER_TELEGRAM_ID", "1")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    monkeypatch.setenv("DB_PATH", "/tmp/custom.db")

    config = load_config()

    assert config.anthropic_model == "claude-sonnet-5"
    assert config.db_path == "/tmp/custom.db"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.config'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/config.py
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    telegram_bot_token: str
    owner_telegram_id: int
    anthropic_api_key: str
    anthropic_model: str
    db_path: str


def load_config() -> Config:
    def _require(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value

    return Config(
        telegram_bot_token=_require("TELEGRAM_BOT_TOKEN"),
        owner_telegram_id=int(_require("OWNER_TELEGRAM_ID")),
        anthropic_api_key=_require("ANTHROPIC_API_KEY"),
        anthropic_model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8"),
        db_path=os.environ.get("DB_PATH", "holodok_agent.db"),
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_config.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/config.py tests/test_config.py
git commit -m "feat: add environment-based config loader"
```

---

### Task 3: SQLite storage layer

**Files:**
- Create: `holodok_agent/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `connect(db_path: str) -> sqlite3.Connection`
  - `save_style_profile(conn, tone_summary: str, lexicon_notes: str, structure_notes: str, raw_samples: list[str]) -> None`
  - `get_style_profile(conn) -> dict | None` — keys `tone_summary`, `lexicon_notes`, `structure_notes`, `raw_samples`, `updated_at`
  - `add_hard_rule(conn, rule_text: str) -> None`
  - `get_hard_rules(conn) -> list[str]`
  - `record_draft(conn, scenario: str) -> int` (returns draft id)
  - `mark_draft_published(conn, draft_id: int) -> None`
  - `save_monthly_metrics(conn, month: str, raw_answer: str) -> None`
  - `get_monthly_metrics(conn, month: str) -> str | None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_db.py
from holodok_agent.db import (
    connect,
    save_style_profile,
    get_style_profile,
    add_hard_rule,
    get_hard_rules,
    record_draft,
    mark_draft_published,
    save_monthly_metrics,
    get_monthly_metrics,
)


def test_get_style_profile_returns_none_when_empty(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    assert get_style_profile(conn) is None


def test_save_and_get_style_profile_roundtrip(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    save_style_profile(conn, "дружелюбный", "просто", "проблема-решение", ["текст 1", "текст 2"])

    profile = get_style_profile(conn)

    assert profile["tone_summary"] == "дружелюбный"
    assert profile["lexicon_notes"] == "просто"
    assert profile["structure_notes"] == "проблема-решение"
    assert profile["raw_samples"] == ["текст 1", "текст 2"]
    assert profile["updated_at"]


def test_save_style_profile_overwrites_previous(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    save_style_profile(conn, "тон1", "лекс1", "структ1", ["a"])
    save_style_profile(conn, "тон2", "лекс2", "структ2", ["b"])

    profile = get_style_profile(conn)

    assert profile["tone_summary"] == "тон2"
    assert profile["raw_samples"] == ["b"]


def test_hard_rules_roundtrip(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    assert get_hard_rules(conn) == []

    add_hard_rule(conn, "никогда не демпинговать")
    add_hard_rule(conn, "гарантия всегда 3 месяца")

    assert get_hard_rules(conn) == ["никогда не демпинговать", "гарантия всегда 3 месяца"]


def test_draft_lifecycle(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    draft_id = record_draft(conn, "vk_post")

    assert isinstance(draft_id, int)

    mark_draft_published(conn, draft_id)
    row = conn.execute("SELECT published_at FROM draft_usage WHERE id = ?", (draft_id,)).fetchone()
    assert row["published_at"] is not None


def test_monthly_metrics_roundtrip(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    assert get_monthly_metrics(conn, "2026-07") is None

    save_monthly_metrics(conn, "2026-07", "5 заявок, часа 3 в неделю")

    assert get_monthly_metrics(conn, "2026-07") == "5 заявок, часа 3 в неделю"


def test_save_monthly_metrics_overwrites_same_month(tmp_path):
    conn = connect(str(tmp_path / "test.db"))
    save_monthly_metrics(conn, "2026-07", "первый ответ")
    save_monthly_metrics(conn, "2026-07", "исправленный ответ")

    assert get_monthly_metrics(conn, "2026-07") == "исправленный ответ"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.db'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/db.py
import json
import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS style_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    tone_summary TEXT NOT NULL,
    lexicon_notes TEXT NOT NULL,
    structure_notes TEXT NOT NULL,
    raw_samples_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hard_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS draft_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario TEXT NOT NULL,
    created_at TEXT NOT NULL,
    published_at TEXT
);

CREATE TABLE IF NOT EXISTS metrics_monthly (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    month TEXT NOT NULL UNIQUE,
    raw_answer TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def save_style_profile(conn, tone_summary, lexicon_notes, structure_notes, raw_samples) -> None:
    conn.execute(
        """
        INSERT INTO style_profile (id, tone_summary, lexicon_notes, structure_notes, raw_samples_json, updated_at)
        VALUES (1, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            tone_summary = excluded.tone_summary,
            lexicon_notes = excluded.lexicon_notes,
            structure_notes = excluded.structure_notes,
            raw_samples_json = excluded.raw_samples_json,
            updated_at = excluded.updated_at
        """,
        (tone_summary, lexicon_notes, structure_notes, json.dumps(raw_samples, ensure_ascii=False), _now()),
    )
    conn.commit()


def get_style_profile(conn) -> dict | None:
    row = conn.execute("SELECT * FROM style_profile WHERE id = 1").fetchone()
    if row is None:
        return None
    return {
        "tone_summary": row["tone_summary"],
        "lexicon_notes": row["lexicon_notes"],
        "structure_notes": row["structure_notes"],
        "raw_samples": json.loads(row["raw_samples_json"]),
        "updated_at": row["updated_at"],
    }


def add_hard_rule(conn, rule_text: str) -> None:
    conn.execute(
        "INSERT INTO hard_rules (rule_text, created_at) VALUES (?, ?)",
        (rule_text, _now()),
    )
    conn.commit()


def get_hard_rules(conn) -> list[str]:
    rows = conn.execute("SELECT rule_text FROM hard_rules ORDER BY id").fetchall()
    return [row["rule_text"] for row in rows]


def record_draft(conn, scenario: str) -> int:
    cursor = conn.execute(
        "INSERT INTO draft_usage (scenario, created_at) VALUES (?, ?)",
        (scenario, _now()),
    )
    conn.commit()
    return cursor.lastrowid


def mark_draft_published(conn, draft_id: int) -> None:
    conn.execute(
        "UPDATE draft_usage SET published_at = ? WHERE id = ?",
        (_now(), draft_id),
    )
    conn.commit()


def save_monthly_metrics(conn, month: str, raw_answer: str) -> None:
    conn.execute(
        """
        INSERT INTO metrics_monthly (month, raw_answer, recorded_at)
        VALUES (?, ?, ?)
        ON CONFLICT(month) DO UPDATE SET raw_answer = excluded.raw_answer, recorded_at = excluded.recorded_at
        """,
        (month, raw_answer, _now()),
    )
    conn.commit()


def get_monthly_metrics(conn, month: str) -> str | None:
    row = conn.execute("SELECT raw_answer FROM metrics_monthly WHERE month = ?", (month,)).fetchone()
    return row["raw_answer"] if row else None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_db.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/db.py tests/test_db.py
git commit -m "feat: add SQLite storage layer for style, rules, drafts, metrics"
```

---

### Task 4: Owner whitelist check

**Files:**
- Create: `holodok_agent/bot/auth.py`
- Test: `tests/test_auth.py`

**Interfaces:**
- Produces: `is_owner(user_id: int, owner_id: int) -> bool`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_auth.py
from holodok_agent.bot.auth import is_owner


def test_is_owner_true_for_matching_id():
    assert is_owner(123, 123) is True


def test_is_owner_false_for_other_id():
    assert is_owner(456, 123) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.bot.auth'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/bot/auth.py
def is_owner(user_id: int, owner_id: int) -> bool:
    return user_id == owner_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_auth.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/auth.py tests/test_auth.py
git commit -m "feat: add owner whitelist check"
```

---

### Task 5: Claude API client wrapper

**Files:**
- Create: `holodok_agent/llm/client.py`
- Test: `tests/test_client.py`

**Interfaces:**
- Consumes: `anthropic.Anthropic` SDK class.
- Produces: `class ClaudeClient` with constructor `ClaudeClient(api_key: str, model: str)` and method `.complete(system: str, user_message: str, max_tokens: int = 1024) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_client.py
from unittest.mock import MagicMock, patch

from holodok_agent.llm.client import ClaudeClient


def test_complete_sends_correct_request_and_extracts_text():
    with patch("holodok_agent.llm.client.Anthropic") as mock_anthropic_cls:
        mock_sdk_client = MagicMock()
        mock_anthropic_cls.return_value = mock_sdk_client

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Готовый текст ответа"
        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_sdk_client.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key", model="claude-opus-4-8")
        result = client.complete(system="системный промпт", user_message="пользовательский запрос")

        assert result == "Готовый текст ответа"
        mock_anthropic_cls.assert_called_once_with(api_key="test-key")
        mock_sdk_client.messages.create.assert_called_once_with(
            model="claude-opus-4-8",
            max_tokens=1024,
            system="системный промпт",
            messages=[{"role": "user", "content": "пользовательский запрос"}],
        )


def test_complete_joins_multiple_text_blocks():
    with patch("holodok_agent.llm.client.Anthropic") as mock_anthropic_cls:
        mock_sdk_client = MagicMock()
        mock_anthropic_cls.return_value = mock_sdk_client

        block_a = MagicMock(type="text", text="Часть 1. ")
        block_b = MagicMock(type="text", text="Часть 2.")
        mock_response = MagicMock()
        mock_response.content = [block_a, block_b]
        mock_sdk_client.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="k", model="claude-opus-4-8")
        result = client.complete(system="s", user_message="u")

        assert result == "Часть 1. Часть 2."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.llm.client'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/llm/client.py
from anthropic import Anthropic


class ClaudeClient:
    def __init__(self, api_key: str, model: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, system: str, user_message: str, max_tokens: int = 1024) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return "".join(block.text for block in response.content if block.type == "text")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_client.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/llm/client.py tests/test_client.py
git commit -m "feat: add Claude API client wrapper"
```

---

### Task 6: Style analysis from uploaded samples

**Files:**
- Create: `holodok_agent/llm/style.py`
- Test: `tests/test_style.py`

**Interfaces:**
- Consumes: `ClaudeClient.complete(system, user_message, max_tokens=1024) -> str` (Task 5).
- Produces: `analyze_style(client: ClaudeClient, samples: list[str]) -> dict` returning `{"tone_summary": str, "lexicon_notes": str, "structure_notes": str}`. Raises `ValueError` if `samples` is empty or the model response can't be parsed.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_style.py
from unittest.mock import MagicMock

import pytest

from holodok_agent.llm.style import analyze_style, _parse_style_response


def test_analyze_style_raises_on_empty_samples():
    with pytest.raises(ValueError, match="хотя бы один"):
        analyze_style(MagicMock(), [])


def test_parse_style_response_extracts_three_sections():
    raw = (
        "ТОН: дружелюбный, простой\n"
        "ЛЕКСИКА: короткие слова, без канцелярита\n"
        "СТРУКТУРА: проблема-решение-цена"
    )

    result = _parse_style_response(raw)

    assert result["tone_summary"] == "дружелюбный, простой"
    assert result["lexicon_notes"] == "короткие слова, без канцелярита"
    assert result["structure_notes"] == "проблема-решение-цена"


def test_parse_style_response_appends_continuation_lines():
    raw = "ТОН: дружелюбный\nи открытый\nЛЕКСИКА: просто\nСТРУКТУРА: списком"

    result = _parse_style_response(raw)

    assert result["tone_summary"] == "дружелюбный и открытый"


def test_parse_style_response_raises_when_section_missing():
    with pytest.raises(ValueError, match="ЛЕКСИКА"):
        _parse_style_response("ТОН: дружелюбный\nСТРУКТУРА: просто")


def test_analyze_style_calls_client_with_joined_samples_and_parses_result():
    mock_client = MagicMock()
    mock_client.complete.return_value = "ТОН: деловой\nЛЕКСИКА: техническая\nСТРУКТУРА: списком"

    result = analyze_style(mock_client, ["текст 1", "текст 2"])

    assert result == {
        "tone_summary": "деловой",
        "lexicon_notes": "техническая",
        "structure_notes": "списком",
    }
    args, kwargs = mock_client.complete.call_args
    assert "текст 1" in kwargs["user_message"]
    assert "текст 2" in kwargs["user_message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_style.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.llm.style'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/llm/style.py
from holodok_agent.llm.client import ClaudeClient

STYLE_ANALYSIS_SYSTEM_PROMPT = (
    "Ты — лингвист-аналитик. Тебе дают несколько текстов объявлений/постов одного автора. "
    "Опиши стиль автора тремя блоками, каждый — 2-4 предложения на русском: "
    "ТОН, ЛЕКСИКА, СТРУКТУРА. Не придумывай факты про автора, только наблюдения о тексте. "
    "Ответь строго в формате:\nТОН: ...\nЛЕКСИКА: ...\nСТРУКТУРА: ..."
)

_MARKERS = {
    "ТОН:": "tone_summary",
    "ЛЕКСИКА:": "lexicon_notes",
    "СТРУКТУРА:": "structure_notes",
}


def analyze_style(client: ClaudeClient, samples: list[str]) -> dict:
    if not samples:
        raise ValueError("Нужен хотя бы один образец текста для анализа стиля")
    joined = "\n\n---\n\n".join(samples)
    raw = client.complete(system=STYLE_ANALYSIS_SYSTEM_PROMPT, user_message=joined)
    return _parse_style_response(raw)


def _parse_style_response(raw: str) -> dict:
    sections = {"tone_summary": "", "lexicon_notes": "", "structure_notes": ""}
    current_key = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        matched = False
        for marker, key in _MARKERS.items():
            if stripped.startswith(marker):
                current_key = key
                sections[key] = stripped[len(marker):].strip()
                matched = True
                break
        if not matched and current_key:
            sections[current_key] = (sections[current_key] + " " + stripped).strip()

    for key, value in sections.items():
        if not value:
            label = next(marker for marker, k in _MARKERS.items() if k == key)
            raise ValueError(f"Не удалось разобрать ответ модели: отсутствует секция {label}")
    return sections
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_style.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/llm/style.py tests/test_style.py
git commit -m "feat: add style analysis from uploaded text samples"
```

---

### Task 7: Hard-rule extraction from chat messages

**Files:**
- Create: `holodok_agent/rules.py`
- Test: `tests/test_rules.py`

**Interfaces:**
- Produces: `extract_rule_from_message(text: str) -> str | None`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_rules.py
from holodok_agent.rules import extract_rule_from_message


def test_extract_rule_from_message_with_comma():
    result = extract_rule_from_message("запомни, я никогда не даю скидку больше 10%")
    assert result == "я никогда не даю скидку больше 10%"


def test_extract_rule_from_message_case_insensitive():
    result = extract_rule_from_message("Запомни: гарантия всегда 3 месяца")
    assert result == "гарантия всегда 3 месяца"


def test_extract_rule_from_message_without_separator():
    result = extract_rule_from_message("запомни цена выезда всегда 300 рублей")
    assert result == "цена выезда всегда 300 рублей"


def test_extract_rule_from_message_returns_none_when_empty():
    assert extract_rule_from_message("запомни") is None
    assert extract_rule_from_message("запомни,   ") is None


def test_extract_rule_from_message_returns_none_for_unrelated_text():
    assert extract_rule_from_message("привет, как дела?") is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.rules'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/rules.py
import re

_REMEMBER_PATTERN = re.compile(r"^\s*запомни[,:]?\s*(.+)$", re.IGNORECASE | re.DOTALL)


def extract_rule_from_message(text: str) -> str | None:
    match = _REMEMBER_PATTERN.match(text)
    if not match:
        return None
    rule = match.group(1).strip()
    return rule or None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_rules.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/rules.py tests/test_rules.py
git commit -m "feat: extract hard rules from remember-style chat messages"
```

---

### Task 8: Content generation scenarios

**Files:**
- Create: `holodok_agent/llm/content.py`
- Test: `tests/test_content.py`

**Interfaces:**
- Consumes: `ClaudeClient.complete(system, user_message, max_tokens=1024) -> str` (Task 5); style profile dict shape from Task 3/6 (`tone_summary`, `lexicon_notes`, `structure_notes`).
- Produces:
  - `SCENARIO_INSTRUCTIONS: dict[str, str]` with keys `"vk_post"`, `"avito_ad"`, `"review_reply"`, `"idea"`.
  - `build_system_prompt(style_profile: dict, hard_rules: list[str]) -> str`
  - `generate_content(client: ClaudeClient, style_profile: dict, hard_rules: list[str], scenario: str, user_input: str) -> str` — raises `ValueError` for unknown scenario.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_content.py
from unittest.mock import MagicMock

import pytest

from holodok_agent.llm.content import build_system_prompt, generate_content, SCENARIO_INSTRUCTIONS

STYLE_PROFILE = {
    "tone_summary": "дружелюбный",
    "lexicon_notes": "просто",
    "structure_notes": "проблема-решение",
}


def test_build_system_prompt_includes_style_and_rules():
    prompt = build_system_prompt(STYLE_PROFILE, ["никогда не демпинговать"])

    assert "дружелюбный" in prompt
    assert "просто" in prompt
    assert "проблема-решение" in prompt
    assert "никогда не демпинговать" in prompt


def test_build_system_prompt_handles_no_rules():
    prompt = build_system_prompt(STYLE_PROFILE, [])
    assert "правил пока нет" in prompt


def test_generate_content_raises_for_unknown_scenario():
    with pytest.raises(ValueError, match="Неизвестный сценарий"):
        generate_content(MagicMock(), STYLE_PROFILE, [], "unknown_scenario", "")


@pytest.mark.parametrize("scenario", list(SCENARIO_INSTRUCTIONS.keys()))
def test_generate_content_calls_client_for_each_known_scenario(scenario):
    mock_client = MagicMock()
    mock_client.complete.return_value = "готовый текст"

    result = generate_content(mock_client, STYLE_PROFILE, [], scenario, "входные данные")

    assert result == "готовый текст"
    mock_client.complete.assert_called_once()
    _, kwargs = mock_client.complete.call_args
    assert SCENARIO_INSTRUCTIONS[scenario] in kwargs["user_message"]


def test_generate_content_without_user_input_uses_instruction_only():
    mock_client = MagicMock()
    mock_client.complete.return_value = "идеи"

    generate_content(mock_client, STYLE_PROFILE, [], "idea", "")

    _, kwargs = mock_client.complete.call_args
    assert kwargs["user_message"] == SCENARIO_INSTRUCTIONS["idea"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_content.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.llm.content'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/llm/content.py
from holodok_agent.llm.client import ClaudeClient

SCENARIO_INSTRUCTIONS = {
    "vk_post": (
        "Напиши пост для ВКонтакте/Telegram от лица мастера по ремонту холодильников. "
        "Пост должен быть готов к публикации без правок."
    ),
    "avito_ad": (
        "Напиши короткий текст объявления для Авито/Юлы о ремонте холодильников. "
        "Кратко, по делу, с УТП в начале."
    ),
    "review_reply": (
        "Ниже — текст отзыва клиента. Напиши вежливый ответ от лица мастера: "
        "поблагодари, при негативе — извинись и предложи решение, без оправданий."
    ),
    "idea": (
        "Предложи 3 темы для поста или объявления на основе контекста ниже. "
        "Для каждой темы — одна строка с сутью и одна строка с тем, как её раскрыть."
    ),
}


def build_system_prompt(style_profile: dict, hard_rules: list[str]) -> str:
    rules_block = "\n".join(f"- {rule}" for rule in hard_rules) if hard_rules else "(правил пока нет)"
    return (
        "Ты пишешь тексты от лица мастера по ремонту холодильников в Симферополе, "
        "строго в его личном стиле, описанном ниже. Никогда не выходи за рамки жёстких правил.\n\n"
        f"ТОН: {style_profile['tone_summary']}\n"
        f"ЛЕКСИКА: {style_profile['lexicon_notes']}\n"
        f"СТРУКТУРА: {style_profile['structure_notes']}\n\n"
        f"Жёсткие правила:\n{rules_block}"
    )


def generate_content(
    client: ClaudeClient,
    style_profile: dict,
    hard_rules: list[str],
    scenario: str,
    user_input: str,
) -> str:
    if scenario not in SCENARIO_INSTRUCTIONS:
        raise ValueError(f"Неизвестный сценарий: {scenario}")
    system_prompt = build_system_prompt(style_profile, hard_rules)
    instruction = SCENARIO_INSTRUCTIONS[scenario]
    user_message = (
        f"{instruction}\n\nВходные данные от мастера:\n{user_input}" if user_input else instruction
    )
    return client.complete(system=system_prompt, user_message=user_message)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_content.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/llm/content.py tests/test_content.py
git commit -m "feat: add scenario-based content generation with style and hard rules"
```

---

### Task 9: Bot keyboards and callback parsing

**Files:**
- Create: `holodok_agent/bot/keyboards.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Produces:
  - `build_scenario_menu() -> InlineKeyboardMarkup` (buttons with `callback_data` `"scenario:vk_post"`, `"scenario:avito_ad"`, `"scenario:review_reply"`, `"scenario:idea"`)
  - `parse_scenario_callback(data: str) -> str`
  - `build_regenerate_and_publish_keyboard(draft_id: int) -> InlineKeyboardMarkup` (callback_data `"regen:<id>"`, `"publish:<id>"`)
  - `parse_draft_callback(data: str) -> tuple[str, int]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_keyboards.py
import pytest

from holodok_agent.bot.keyboards import (
    build_scenario_menu,
    parse_scenario_callback,
    build_regenerate_and_publish_keyboard,
    parse_draft_callback,
)


def test_build_scenario_menu_has_four_buttons_with_expected_callbacks():
    menu = build_scenario_menu()
    buttons = [btn for row in menu.inline_keyboard for btn in row]

    callbacks = {btn.callback_data for btn in buttons}
    assert callbacks == {"scenario:vk_post", "scenario:avito_ad", "scenario:review_reply", "scenario:idea"}


def test_parse_scenario_callback_extracts_key():
    assert parse_scenario_callback("scenario:idea") == "idea"


def test_parse_scenario_callback_rejects_unknown_prefix():
    with pytest.raises(ValueError):
        parse_scenario_callback("publish:5")


def test_build_regenerate_and_publish_keyboard_has_two_buttons():
    keyboard = build_regenerate_and_publish_keyboard(42)
    buttons = keyboard.inline_keyboard[0]

    assert buttons[0].callback_data == "regen:42"
    assert buttons[1].callback_data == "publish:42"


def test_parse_draft_callback_extracts_action_and_id():
    assert parse_draft_callback("publish:42") == ("publish", 42)
    assert parse_draft_callback("regen:7") == ("regen", 7)


def test_parse_draft_callback_rejects_bad_id():
    with pytest.raises(ValueError):
        parse_draft_callback("publish:abc")


def test_parse_draft_callback_rejects_unknown_action():
    with pytest.raises(ValueError):
        parse_draft_callback("delete:1")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.bot.keyboards'`

- [ ] **Step 3: Write the implementation**

```python
# holodok_agent/bot/keyboards.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_keyboards.py -v`
Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add holodok_agent/bot/keyboards.py tests/test_keyboards.py
git commit -m "feat: add scenario menu and draft action keyboards"
```

---

### Task 10: Bot handlers — onboarding, scenarios, rules, publish tracking

**Files:**
- Create: `holodok_agent/bot/handlers.py`
- Create: `holodok_agent/bot/main.py`
- Test: `tests/test_handlers.py`

**Interfaces:**
- Consumes: `db.*` (Task 3), `is_owner` (Task 4), `ClaudeClient` (Task 5), `analyze_style` (Task 6), `extract_rule_from_message` (Task 7), `generate_content` (Task 8), keyboard builders/parsers (Task 9), `Config`/`load_config` (Task 2).
- Produces:
  - `build_router(owner_id: int) -> aiogram.Router`
  - FSM state groups `Onboarding`, `ScenarioFlow`, `MetricsFlow` (the latter consumed by Task 11's scheduler).
  - `run() -> None` / `main() -> None` entrypoint in `holodok_agent/bot/main.py`.

- [ ] **Step 1: Write the failing tests for the pure/testable handler behavior**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.bot.handlers'`

- [ ] **Step 3: Write `holodok_agent/bot/handlers.py`**

```python
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
    profile = analyze_style(claude_client, samples)
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
    text = generate_content(claude_client, profile, hard_rules, scenario, user_input)
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
```

- [ ] **Step 4: Write `holodok_agent/bot/main.py`**

```python
# holodok_agent/bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from holodok_agent.bot.handlers import build_router
from holodok_agent.config import load_config
from holodok_agent.db import connect
from holodok_agent.llm.client import ClaudeClient


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

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_handlers.py -v`
Expected: 9 passed

- [ ] **Step 6: Manual smoke test (not automatable without live Telegram/Claude credentials)**

Create a throwaway Telegram bot via @BotFather, set `TELEGRAM_BOT_TOKEN`/`OWNER_TELEGRAM_ID`/`ANTHROPIC_API_KEY` in `.env`, then:

```bash
set -a; source .env; set +a
python -m holodok_agent.bot.main
```

In Telegram, message the bot as the owner:
1. Send `/start` → expect the onboarding prompt (`ONBOARDING_PROMPT` text).
2. Send 2 short sample texts, then `/done` → expect "Стиль запомнил!" followed by the scenario menu with 4 buttons.
3. Tap "Дай идею" → expect a generated reply with «Переделай»/«Опубликовал» buttons.
4. Tap "Опубликовал" → expect the buttons to disappear and a confirmation.
5. Send `запомни, никогда не демпинговать` → expect "Запомнил: никогда не демпинговать".
6. From a second, non-owner Telegram account, send `/start` → expect no reply at all (whitelist working).

- [ ] **Step 7: Commit**

```bash
git add holodok_agent/bot/handlers.py holodok_agent/bot/main.py tests/test_handlers.py
git commit -m "feat: wire onboarding, scenario, rule-memory and publish-tracking handlers"
```

---

### Task 11: Monthly metrics prompt scheduler

**Files:**
- Create: `holodok_agent/bot/scheduler.py`
- Modify: `holodok_agent/bot/main.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `MetricsFlow.waiting_for_monthly_answer` state (Task 10).
- Produces:
  - `MONTHLY_METRICS_PROMPT: str`
  - `send_monthly_metrics_prompt(bot, owner_id: int, storage) -> None`
  - `schedule_monthly_metrics_prompt(scheduler, bot, owner_id: int, storage) -> None`

- [ ] **Step 1: Write the failing tests**

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'holodok_agent.bot.scheduler'`

- [ ] **Step 3: Write the implementation**

```python
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
```

- [ ] **Step 4: Modify `holodok_agent/bot/main.py` to start the scheduler**

```python
# holodok_agent/bot/main.py
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from holodok_agent.bot.handlers import build_router
from holodok_agent.bot.scheduler import schedule_monthly_metrics_prompt
from holodok_agent.config import load_config
from holodok_agent.db import connect
from holodok_agent.llm.client import ClaudeClient


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

    scheduler = AsyncIOScheduler()
    schedule_monthly_metrics_prompt(scheduler, bot, config.owner_telegram_id, dp.storage)
    scheduler.start()

    await dp.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/test_scheduler.py -v`
Expected: 2 passed

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest -v`
Expected: all tests pass (config, db, auth, client, style, rules, content, keyboards, handlers, scheduler)

- [ ] **Step 7: Commit**

```bash
git add holodok_agent/bot/scheduler.py holodok_agent/bot/main.py tests/test_scheduler.py
git commit -m "feat: schedule monthly metrics prompt on the 1st of each month"
```

---

### Task 12: Deployment as a systemd service

**Files:**
- Create: `deploy/holodok-agent.service`
- Create: `README.md`

**Interfaces:**
- Consumes: `holodok_agent.bot.main:main` (Task 11).

- [ ] **Step 1: Write the systemd unit file**

```ini
# deploy/holodok-agent.service
[Unit]
Description=Holodok Agent Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=/opt/holodok-agent
EnvironmentFile=/opt/holodok-agent/.env
ExecStart=/opt/holodok-agent/.venv/bin/python -m holodok_agent.bot.main
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

- [ ] **Step 2: Write `README.md` with setup and run instructions**

```markdown
# Holodok Agent

Личный Telegram-бот-помощник мастера по ремонту холодильников. См. [spec.md](spec.md) и план в `docs/superpowers/plans/`.

## Локальный запуск

\`\`\`bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID, ANTHROPIC_API_KEY
python -m pytest
python -m holodok_agent.bot.main
\`\`\`

## Деплой на VPS (systemd)

\`\`\`bash
sudo mkdir -p /opt/holodok-agent
sudo cp -r . /opt/holodok-agent
cd /opt/holodok-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # заполнить реальные значения
sudo cp deploy/holodok-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now holodok-agent
sudo systemctl status holodok-agent
\`\`\`

Логи: \`journalctl -u holodok-agent -f\`
```

- [ ] **Step 3: Manual verification on the target VPS**

```bash
sudo systemctl status holodok-agent
```

Expected: `active (running)`. Then repeat the Task 10 Telegram smoke-test checklist against the deployed bot.

- [ ] **Step 4: Commit**

```bash
git add deploy/holodok-agent.service README.md
git commit -m "chore: add systemd deployment unit and setup instructions"
```

---

## Self-Review Notes

- **Spec coverage**: обучение стилю (§5, Task 6/10), кнопки-сценарии + «Переделай» (§5, Task 8-10), «Ответ на отзыв» вручную (§5, Task 10 `review_reply` input prompt), «запомни правило» (§5/§10.4, Task 7/10), whitelist-доступ (§8, Task 4/10), метрики — использованные черновики (Task 10 `handle_publish`) и ежемесячная субъективная оценка (§4, Task 11) — все покрыты. Авито/Юла, еженедельный отчёт, горячие лиды сознательно вне этого плана (см. «Scope of this plan» выше) — будут отдельными планами.
- **No placeholders**: весь код в шагах — рабочий, без TBD; единственное отклонение от чистого TDD — Task 10 Step 6 и Task 12 Step 3, которые являются ручными smoke-тестами (нужны реальные Telegram/Claude credentials, которые недоступны в автоматическом тестовом прогоне) — оформлены как конкретные шаги с точными ожидаемыми результатами, а не общими фразами.
- **Type consistency**: `ClaudeClient.complete(system, user_message, max_tokens=1024) -> str` используется одинаково в Task 6 и Task 8. `db.get_style_profile(conn) -> dict | None` с ключами `tone_summary`/`lexicon_notes`/`structure_notes`/`raw_samples`/`updated_at` используется одинаково в Task 6 (форма результата `analyze_style`) и Task 10 (`_generate_and_send`). Ключи сценариев (`vk_post`, `avito_ad`, `review_reply`, `idea`) совпадают между `SCENARIO_INSTRUCTIONS` (Task 8), `SCENARIO_INPUT_PROMPTS` (Task 10) и callback_data в Task 9.
