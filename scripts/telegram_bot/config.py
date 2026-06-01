from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from scripts.job_creation.env import get_env_secret
from scripts.job_creation.paths import ROOT


@dataclass(frozen=True)
class BotConfig:
    token: str
    allowed_chat_ids: set[int]
    master_data_path: Path
    database_path: Path


def _required(name: str) -> str:
    value = get_env_secret(name)
    if not value:
        raise ValueError(f"{name} must be configured in the environment, .env.local, or .env")
    return value


def load_config() -> BotConfig:
    master_data = os.environ.get("CV_MASTER_DATA")
    if not master_data:
        raise ValueError("CV_MASTER_DATA must be explicitly configured for the Telegram bot")
    path = Path(master_data)
    master_data_path = path if path.is_absolute() else ROOT / path
    if not master_data_path.exists():
        raise ValueError(f"CV_MASTER_DATA file does not exist: {master_data_path}")
    allowed = {int(value.strip()) for value in _required("TELEGRAM_ALLOWED_CHAT_IDS").split(",")}
    database = os.environ.get("TELEGRAM_STATE_DB", "data/telegram_bot.sqlite3")
    database_path = Path(database)
    if not database_path.is_absolute():
        database_path = ROOT / database_path
    return BotConfig(_required("TELEGRAM_BOT_TOKEN"), allowed, master_data_path, database_path)
