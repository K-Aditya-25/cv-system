from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .env import get_env_secret
from .errors import IntakeError

DEFAULT_TENSORIX_BASE_URL = "https://api.tensorix.ai/v1"
DEFAULT_ROUTER_MODEL = "minimax/minimax-m2.5"


def tensorix_chat(system_prompt: str, user_prompt: str, request_timeout: float = 30) -> str:
    api_key = get_env_secret("TENSORIX_API_KEY")
    if not api_key:
        raise IntakeError("TENSORIX_API_KEY is not set in the environment, .env.local, or .env")
    base_url = os.environ.get("CV_ROUTER_BASE_URL", DEFAULT_TENSORIX_BASE_URL).rstrip("/")
    payload = {
        "model": os.environ.get("CV_ROUTER_MODEL", DEFAULT_ROUTER_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": 500,
    }
    request = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {api_key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=request_timeout) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise IntakeError(f"Tensorix router request failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise IntakeError(f"Tensorix router request failed: {exc.reason}") from exc
    return _message_content(response_payload)


def _message_content(payload: dict) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise IntakeError("Tensorix router response did not contain choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise IntakeError("Tensorix router response did not contain message text")
    return content.strip()
