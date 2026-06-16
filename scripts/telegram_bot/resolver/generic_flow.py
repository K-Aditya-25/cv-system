from __future__ import annotations

from scripts.telegram_bot.resolver_models import JobMetadata, ResolutionRequest, ResolutionResult
from .extract import listing_urls
from .fetch import FetchError
from .ranking import rank_candidates


def resolve_generic(service, request: ResolutionRequest) -> ResolutionResult:
    result = service._attempt(request.url)
    if result:
        return result
    if service.browser:
        result = service._attempt(request.url, rendered=True)
        if result:
            return result
    if request.mode == "explicit":
        result = _listing(service, request.url)
        if result:
            return result
        return ResolutionResult("fallback_text", reason="explicit link could not be resolved")
    if service.discover:
        query = _query(request)
        service.progress("discover", query)
        outcome = service.discover.search(query) if hasattr(service.discover, "search") else service.discover(query)
        candidates = outcome.candidates if hasattr(outcome, "candidates") else outcome
        for candidate in rank_candidates(candidates, request.url):
            result = service._attempt(candidate)
            if result:
                return result
    return ResolutionResult("needs_explicit_link", reason="automatic resolution did not find a posting")


def _query(request: ResolutionRequest) -> str:
    metadata = request.inferred or JobMetadata()
    return " ".join(filter(None, (metadata.company, metadata.role, metadata.location))) or request.url


def _listing(service, url: str) -> ResolutionResult | None:
    try:
        page = service._page(url)
        html = page.body.decode("utf-8", errors="replace")
        urls = rank_candidates(listing_urls(html, page.final_url), page.final_url)
    except (FetchError, ValueError, OSError):
        return None
    for candidate in urls[:10]:
        result = service._attempt(candidate) if candidate != page.final_url else None
        if result:
            return result
    return None
