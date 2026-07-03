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
