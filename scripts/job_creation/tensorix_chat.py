from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .chat_response import chat_message_text
from .env import get_env_secret
from .errors import IntakeError

DEFAULT_TENSORIX_BASE_URL = "https://api.tensorix.ai/v1"
DEFAULT_ROUTER_MODEL = "minimax/minimax-m2.5"


def tensorix_chat(
    system_prompt: str,
    user_prompt: str,
    request_timeout: float = 30,
    *,
    model: str | None = None,
    max_tokens: int = 500,
    purpose: str = "Tensorix router",
) -> str:
    api_key = get_env_secret("TENSORIX_API_KEY")
    if not api_key:
        raise IntakeError("TENSORIX_API_KEY is not set in the environment, .env.local, or .env")
    base_url = (
        os.environ.get("CV_TENSORIX_BASE_URL")
        or os.environ.get("TENSORIX_BASE_URL")
        or os.environ.get("CV_ROUTER_BASE_URL")
        or DEFAULT_TENSORIX_BASE_URL
    ).rstrip("/")
    payload = {
        "model": model or os.environ.get("CV_ROUTER_MODEL", DEFAULT_ROUTER_MODEL),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
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
        raise IntakeError(f"{purpose} request failed: HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise IntakeError(f"{purpose} request failed: {exc.reason}") from exc
    return chat_message_text(response_payload, purpose)
