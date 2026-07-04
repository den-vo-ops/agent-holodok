import pytest

from holodok_agent.config import load_config


def test_load_config_raises_when_token_missing(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    monkeypatch.setenv("ADMIN_IDS", "12345")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with pytest.raises(RuntimeError, match="BOT_TOKEN"):
        load_config()


def test_load_config_reads_all_values_with_default_model(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "test-token")
    monkeypatch.setenv("ADMIN_IDS", "12345")
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("DB_PATH", raising=False)

    config = load_config()

    assert config.bot_token == "test-token"
    assert config.owner_id == 12345
    assert config.groq_api_key == "test-key"
    assert config.groq_model == "llama-3.3-70b-versatile"
    assert config.db_path == "holodok_agent.db"


def test_load_config_respects_overrides(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_IDS", "1")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("GROQ_MODEL", "llama-3.1-8b-instant")
    monkeypatch.setenv("DB_PATH", "/tmp/custom.db")

    config = load_config()

    assert config.groq_model == "llama-3.1-8b-instant"
    assert config.db_path == "/tmp/custom.db"


def test_load_config_takes_first_of_multiple_admin_ids(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "t")
    monkeypatch.setenv("ADMIN_IDS", "7206977258, 999")
    monkeypatch.setenv("GROQ_API_KEY", "k")

    config = load_config()

    assert config.owner_id == 7206977258
