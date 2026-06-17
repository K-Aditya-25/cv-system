from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def log_event(name: str, **fields: Any) -> None:
    values = [
        f"{key}={_format(value)}"
        for key, value in fields.items()
        if value is not None and value != ""
    ]
    print(f"[{name}] {' '.join(values)}", flush=True)


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def safe_error(error: Exception) -> str:
    message = str(error).replace("\n", " ")
    return message[:240]


def _format(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, Path):
        return json.dumps(str(value))
    if isinstance(value, str):
        return json.dumps(value)
    return str(value)
