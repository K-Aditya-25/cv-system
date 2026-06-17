from __future__ import annotations

import os

from .errors import IntakeError
from .llm import call_anthropic
from .tensorix_chat import tensorix_chat
from .text_utils import normalize_provider


def call_model(system_prompt: str, user_prompt: str, provider: str, model: str) -> str:
    normalized = normalize_provider(provider)
    if normalized == "claude":
        return call_anthropic(system_prompt, user_prompt, model)
    if normalized == "tensorix":
        return tensorix_chat(
            system_prompt,
            user_prompt,
            _tensorix_timeout(),
            model=model,
            max_tokens=_tensorix_max_tokens(),
            purpose="Tensorix CV model",
        )
    raise IntakeError(f"Unsupported provider: {provider}")


def _tensorix_timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("CV_TENSORIX_TIMEOUT_SECONDS", "120")))
    except ValueError:
        return 120.0


def _tensorix_max_tokens() -> int:
    try:
        return max(1000, int(os.environ.get("CV_TENSORIX_MAX_TOKENS", "12000")))
    except ValueError:
        return 12000
