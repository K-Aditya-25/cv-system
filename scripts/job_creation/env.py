from __future__ import annotations

import os

from .constants import LOCAL_ENV_FILES
from .paths import ROOT

def parse_env_line(line: str, env_name: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    if key.strip() != env_name:
        return None
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        value = value[1:-1]
    return value or None


def get_env_secret(env_name: str) -> str | None:
    value = os.environ.get(env_name)
    if value:
        return value
    for env_file in LOCAL_ENV_FILES:
        path = ROOT / env_file
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            value = parse_env_line(line, env_name)
            if value:
                return value
    return None

