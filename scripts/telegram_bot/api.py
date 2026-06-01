from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from .multipart import document_body


class TelegramApi:
    def __init__(self, token: str):
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self.file_url = f"https://api.telegram.org/file/bot{token}/"

    def _json(self, method: str, data: dict[str, Any] | None = None) -> Any:
        body = json.dumps(data or {}).encode()
        request = urllib.request.Request(
            self.base_url + method, body, {"Content-Type": "application/json"}, method="POST",
        )
        with self._open(request, 45) as response:
            payload = json.loads(response.read())
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", f"Telegram {method} failed"))
        return payload["result"]

    def _open(self, request: urllib.request.Request | str, timeout: int) -> Any:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return urllib.request.urlopen(request, timeout=timeout)
            except Exception as exc:
                last_error = exc
                if attempt < 2:
                    time.sleep(2**attempt)
        raise RuntimeError(f"Telegram request failed after retries: {last_error}") from last_error

    def get_me(self) -> dict[str, Any]:
        return self._json("getMe")

    def delete_webhook(self, *, drop_pending_updates: bool = False) -> None:
        self._json("deleteWebhook", {"drop_pending_updates": drop_pending_updates})

    def set_commands(self, commands: list[dict[str, str]]) -> None:
        self._json("setMyCommands", {"commands": commands})

    def updates(self, offset: int | None) -> list[dict[str, Any]]:
        data: dict[str, Any] = {"timeout": 30, "allowed_updates": ["message"]}
        if offset is not None:
            data["offset"] = offset
        return self._json("getUpdates", data)

    def send_message(self, chat_id: int, text: str) -> None:
        for start in range(0, len(text), 4000):
            self._json("sendMessage", {"chat_id": chat_id, "text": text[start:start + 4000]})

    def send_document(self, chat_id: int, path: Path) -> None:
        body, content_type = document_body(chat_id, path)
        request = urllib.request.Request(
            self.base_url + "sendDocument", body, {"Content-Type": content_type}, method="POST",
        )
        with self._open(request, 90) as response:
            payload = json.loads(response.read())
        if not payload.get("ok"):
            raise RuntimeError(payload.get("description", "Telegram sendDocument failed"))

    def download_text(self, file_id: str) -> str:
        file_path = self._json("getFile", {"file_id": file_id})["file_path"]
        with self._open(self.file_url + urllib.parse.quote(file_path), 45) as response:
            content = response.read(250_001)
        if len(content) > 250_000:
            raise ValueError("Job description .txt files must not exceed 250 KB")
        return content.decode("utf-8")
