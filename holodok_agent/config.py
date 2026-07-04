import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    groq_api_key: str
    groq_model: str
    db_path: str


def load_config() -> Config:
    def _require(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"Missing required environment variable: {name}")
        return value

    # ADMIN_IDS может быть одним id или списком через запятую — берём первый как
    # единственного владельца (проект однопользовательский, см. spec §3).
    owner_id = int(_require("ADMIN_IDS").split(",")[0].strip())

    return Config(
        bot_token=_require("BOT_TOKEN"),
        owner_id=owner_id,
        groq_api_key=_require("GROQ_API_KEY"),
        groq_model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        db_path=os.environ.get("DB_PATH", "holodok_agent.db"),
    )
