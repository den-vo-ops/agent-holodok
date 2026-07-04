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
    has_onboarded,
    mark_onboarded,
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
