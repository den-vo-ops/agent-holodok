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
