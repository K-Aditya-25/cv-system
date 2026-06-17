from __future__ import annotations

from typing import Any

from .llm import parse_llm_json
from .model_logging import log_event, safe_error, text_hash


def parse_logged_llm_json(
    raw_text: str,
    provider: str,
    model: str,
    attempt: int,
) -> dict[str, Any]:
    try:
        payload = parse_llm_json(raw_text)
    except Exception as exc:
        log_event(
            "llm.parse_error", provider=provider, model=model, attempt=attempt,
            raw_chars=len(raw_text), raw_sha=text_hash(raw_text),
            error_type=type(exc).__name__, error=safe_error(exc),
        )
        raise
    log_event(
        "llm.parse_ok", provider=provider, model=model, attempt=attempt,
        raw_chars=len(raw_text), raw_sha=text_hash(raw_text),
        keys=",".join(sorted(str(key) for key in payload.keys())),
    )
    return payload
