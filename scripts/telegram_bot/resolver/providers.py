from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol

from scripts.job_creation.env import get_env_secret
from scripts.telegram_bot.resolver_models import SearchCandidate


@dataclass(frozen=True)
class SearchOutcome:
    provider: str
    candidates: tuple[SearchCandidate, ...] = ()
    unavailable_reason: str | None = None

    @property
    def available(self) -> bool:
        return self.unavailable_reason is None


class SearchProvider(Protocol):
    name: str

    def search(self, query: str, *, limit: int) -> SearchOutcome: ...


class _JsonProvider:
    name = ""
    secret_name = ""

    def search(self, query: str, *, limit: int) -> SearchOutcome:
        key = get_env_secret(self.secret_name)
        if not key:
            return SearchOutcome(self.name, unavailable_reason=f"{self.secret_name} is not set")
        try:
            payload = self._request(key, query, max(1, min(limit, 10)))
            candidates = tuple(self._candidates(payload))
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
            return SearchOutcome(self.name, unavailable_reason=str(exc))
        return SearchOutcome(self.name, candidates)

    def _request(self, key: str, query: str, limit: int) -> dict[str, Any]:
        raise NotImplementedError

    def _candidates(self, payload: dict[str, Any]) -> list[SearchCandidate]:
        raise NotImplementedError


class TavilySearchProvider(_JsonProvider):
    name, secret_name = "tavily", "TAVILY_API_KEY"

    def _request(self, key: str, query: str, limit: int) -> dict[str, Any]:
        body = json.dumps({"query": query, "search_depth": "basic", "max_results": limit}).encode()
        request = urllib.request.Request("https://api.tavily.com/search", body, {
            "Authorization": f"Bearer {key}", "Content-Type": "application/json",
        }, method="POST")
        return _open_json(request)

    def _candidates(self, payload: dict[str, Any]) -> list[SearchCandidate]:
        return [_candidate(self.name, item, "content", item.get("score")) for item in payload["results"]]


class BraveSearchProvider(_JsonProvider):
    name, secret_name = "brave", "BRAVE_SEARCH_API_KEY"

    def _request(self, key: str, query: str, limit: int) -> dict[str, Any]:
        params = urllib.parse.urlencode({"q": query, "count": limit})
        request = urllib.request.Request(
            f"https://api.search.brave.com/res/v1/web/search?{params}",
            headers={"X-Subscription-Token": key, "Accept": "application/json"},
        )
        return _open_json(request)

    def _candidates(self, payload: dict[str, Any]) -> list[SearchCandidate]:
        return [_candidate(self.name, item, "description") for item in payload["web"]["results"]]


def _open_json(request: urllib.request.Request) -> dict[str, Any]:
    with urllib.request.urlopen(request, timeout=15) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("provider response was not a JSON object")
    return payload


def _candidate(provider: str, item: Any, snippet_key: str, score: Any = None) -> SearchCandidate:
    if not isinstance(item, dict) or not isinstance(item.get("url"), str):
        raise ValueError("provider returned a malformed search result")
    return SearchCandidate(item["url"], str(item.get("title", "")), str(item.get(snippet_key, "")),
                           provider, float(score) if isinstance(score, (int, float)) else 0.0)
