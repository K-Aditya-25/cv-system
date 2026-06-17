from __future__ import annotations

import os

from .errors import IntakeError
from .llm import call_anthropic
from .model_logging import log_event, safe_error, text_hash
from .tensorix_chat import tensorix_chat
from .text_utils import normalize_provider


def call_model(system_prompt: str, user_prompt: str, provider: str, model: str) -> str:
    normalized = normalize_provider(provider)
    log_event(
        "llm.model_call", provider=normalized, model=model,
        system_chars=len(system_prompt), user_chars=len(user_prompt),
    )
    try:
        text = _call_model(system_prompt, user_prompt, normalized, model)
    except Exception as exc:
        log_event(
            "llm.model_error", provider=normalized, model=model,
            error_type=type(exc).__name__, error=safe_error(exc),
        )
        raise
    log_event(
        "llm.model_output", provider=normalized, model=model,
        output_chars=len(text), output_sha=text_hash(text),
    )
    return text


def _call_model(system_prompt: str, user_prompt: str, provider: str, model: str) -> str:
    if provider == "claude":
        return call_anthropic(system_prompt, user_prompt, model)
    if provider == "tensorix":
        return tensorix_chat(
            system_prompt, user_prompt, _tensorix_timeout(), model=model,
            max_tokens=_tensorix_max_tokens(), purpose="Tensorix CV model",
            attempts=_tensorix_attempts(), response_format={"type": "json_object"},
        )
    raise IntakeError(f"Unsupported provider: {provider}")


def _tensorix_timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("CV_TENSORIX_TIMEOUT_SECONDS", "240")))
    except ValueError:
        return 240.0


def _tensorix_max_tokens() -> int:
    try:
        return max(1000, int(os.environ.get("CV_TENSORIX_MAX_TOKENS", "12000")))
    except ValueError:
        return 12000


def _tensorix_attempts() -> int:
    try:
        return max(1, int(os.environ.get("CV_TENSORIX_ATTEMPTS", "3")))
    except ValueError:
        return 3
