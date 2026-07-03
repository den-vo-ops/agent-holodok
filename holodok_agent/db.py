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
