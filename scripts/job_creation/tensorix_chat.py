from __future__ import annotations

import http.client
import json
import os
import time
import urllib.error
import urllib.request
from typing import Any

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
    attempts: int = 1,
    response_format: dict[str, str] | None = None,
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
    if response_format is not None:
        payload["response_format"] = response_format
    data = json.dumps(payload).encode("utf-8")
    url = f"{base_url}/chat/completions"
    headers = {"content-type": "application/json", "authorization": f"Bearer {api_key}"}
    response_payload = _post_json(url, data, headers, request_timeout, purpose, attempts)
    return chat_message_text(response_payload, purpose)


def _post_json(
    url: str,
    data: bytes,
    headers: dict[str, str],
    timeout: float,
    purpose: str,
    attempts: int,
) -> dict[str, Any]:
    attempts = max(1, attempts)
    last_error: Exception | None = None
    for attempt in range(attempts):
        request = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if not _retry_http(exc) or attempt == attempts - 1:
                details = exc.read().decode("utf-8", errors="replace")
                raise IntakeError(f"{purpose} request failed: HTTP {exc.code}: {details}") from exc
            last_error = exc
        except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError) as exc:
            if attempt == attempts - 1:
                raise IntakeError(f"{purpose} request failed after {attempts} attempt(s): {exc}") from exc
            last_error = exc
        time.sleep(min(2 ** attempt, 8))
    raise IntakeError(f"{purpose} request failed after {attempts} attempt(s): {last_error}")


def _retry_http(exc: urllib.error.HTTPError) -> bool:
    return exc.code in {408, 409, 425, 429} or exc.code >= 500
