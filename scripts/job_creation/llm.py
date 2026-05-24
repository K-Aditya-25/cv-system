from __future__ import annotations

import json, os, re, urllib.error, urllib.request
from typing import Any

from .constants import DEFAULT_ANTHROPIC_VERSION
from .env import get_env_secret
from .errors import IntakeError

def strip_json_fences(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_llm_json(raw_text: str) -> dict[str, Any]:
    text = strip_json_fences(raw_text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise IntakeError(f"LLM response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise IntakeError("LLM response must be a JSON object")
    return payload


def call_anthropic(system_prompt: str, user_prompt: str, model: str) -> str:
    api_key = get_env_secret("ANTHROPIC_API_KEY")
    if not api_key:
        raise IntakeError("ANTHROPIC_API_KEY is not set in the environment, .env.local, or .env")

    request_payload = {
        "model": model,
        "max_tokens": 6000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    request = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(request_payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": os.environ.get(
                "ANTHROPIC_VERSION", DEFAULT_ANTHROPIC_VERSION
            ),
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise IntakeError(f"Anthropic API request failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise IntakeError(f"Anthropic API request failed: {exc.reason}") from exc

    content = response_payload.get("content", [])
    text_parts = [part.get("text", "") for part in content if part.get("type") == "text"]
    text = "\n".join(part for part in text_parts if part).strip()
    if not text:
        raise IntakeError("Anthropic API response did not contain text")
    return text

