from __future__ import annotations

from typing import Any

from .errors import IntakeError


def chat_message_text(payload: dict[str, Any], purpose: str) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise IntakeError(f"{purpose} response did not contain choices")
    choice = choices[0] if isinstance(choices[0], dict) else {}
    message = choice.get("message") or {}
    for value in (
        message.get("content"),
        message.get("text"),
        choice.get("text"),
        payload.get("output_text"),
    ):
        text = _content_text(value)
        if text:
            return text
    raise IntakeError(_empty_message_error(purpose, choice, message))


def _content_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(
            text for text in (_content_text(item) for item in value) if text
        ).strip()
    if isinstance(value, dict):
        for key in ("text", "content", "output_text"):
            text = _content_text(value.get(key))
            if text:
                return text
    return ""


def _empty_message_error(purpose: str, choice: dict[str, Any], message: dict[str, Any]) -> str:
    content = message.get("content")
    details = {
        "finish_reason": choice.get("finish_reason"),
        "message_keys": sorted(str(key) for key in message.keys()),
        "content_type": type(content).__name__,
    }
    detail_text = ", ".join(f"{key}={value}" for key, value in details.items())
    return f"{purpose} response did not contain message text ({detail_text})"
