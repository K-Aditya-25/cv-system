from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator

from scripts.telegram_bot.resolver_models import SearchCandidate

from .providers import (
    BraveSearchProvider,
    SearchOutcome,
    SearchProvider,
    TavilySearchProvider,
)


@dataclass(frozen=True)
class DiscoveryOutcome:
    candidates: tuple[SearchCandidate, ...] = ()
    attempts: tuple[SearchOutcome, ...] = ()

    @property
    def available(self) -> bool:
        return bool(self.candidates)

    @property
    def urls(self) -> tuple[str, ...]:
        return tuple(candidate.url for candidate in self.candidates)

    def __iter__(self) -> Iterator[str]:
        return iter(self.urls)


class DiscoveryService:
    def __init__(self, providers: Iterable[SearchProvider] | None = None):
        defaults = (TavilySearchProvider(), BraveSearchProvider())
        self.providers = tuple(defaults if providers is None else providers)

    def search(self, query: str, *, limit: int = 5) -> DiscoveryOutcome:
        attempts: list[SearchOutcome] = []
        for provider in self.providers:
            outcome = provider.search(query, limit=limit)
            attempts.append(outcome)
            if outcome.candidates:
                return DiscoveryOutcome(outcome.candidates, tuple(attempts))
        return DiscoveryOutcome(attempts=tuple(attempts))


def discover(query: str, *, limit: int = 5) -> DiscoveryOutcome:
    return DiscoveryService().search(query, limit=limit)


def discover_urls(query: str, *, limit: int = 5) -> tuple[str, ...]:
    return discover(query, limit=limit).urls
