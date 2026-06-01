from __future__ import annotations

from scripts.telegram_bot.resolver_models import (
    ExtractedPosting, FetchedPage, JobMetadata, ResolutionRequest, ResolutionResult,
)

from .discovery import DiscoveryService
from .extract import ExtractionError, extract_page, listing_urls
from .fetch import FetchError, fetch_html
from .ranking import rank_candidates
from .security import validate_public_https_url


class ResolverService:
    def __init__(self, *, fetch=fetch_html, extract=extract_page, browser=None, discover=None,
                 validate=validate_public_https_url, progress=None) -> None:
        self.fetch = fetch
        self.extract = extract
        self.browser = browser
        self.discover = DiscoveryService() if discover is None else discover
        self.validate = validate
        self.progress = progress or (lambda _stage, _url: None)

    def _page(self, url: str, rendered=False) -> FetchedPage:
        if not rendered:
            page = self.fetch(url)
            if isinstance(page, FetchedPage):
                return page
            return FetchedPage(url, page.url, "text/html; charset=utf-8", page.html.encode())
        page = self.browser.render(url, validate_url=self.validate)
        if page is None:
            raise FetchError("browser did not return a page")
        return FetchedPage(url, page.url, "text/html; charset=utf-8", page.html.encode())

    def _attempt(self, url: str, rendered: bool = False) -> ResolutionResult | None:
        self.progress("render" if rendered else "fetch", url)
        try:
            posting = self.extract(self._page(url, rendered))
            if not isinstance(posting, ExtractedPosting):
                metadata = JobMetadata(posting.company, posting.title, posting.location)
                posting = ExtractedPosting(posting.description, metadata, url)
            return ResolutionResult("resolved", posting=posting, metadata=posting.metadata)
        except (FetchError, ExtractionError, ValueError, OSError):
            return None

    def _query(self, request: ResolutionRequest) -> str:
        metadata = request.inferred or JobMetadata()
        return " ".join(filter(None, (metadata.company, metadata.role, metadata.location))) or request.url

    def _listing(self, url: str) -> ResolutionResult | None:
        try:
            page = self._page(url)
            html = page.body.decode("utf-8", errors="replace")
            urls = rank_candidates(listing_urls(html, page.final_url), page.final_url)
        except (FetchError, ValueError, OSError):
            return None
        for candidate in urls[:10]:
            result = self._attempt(candidate) if candidate != page.final_url else None
            if result:
                return result
        return None

    def resolve(self, request: ResolutionRequest) -> ResolutionResult:
        result = self._attempt(request.url)
        if result:
            return result
        if self.browser:
            result = self._attempt(request.url, rendered=True)
            if result:
                return result
        if request.mode == "explicit":
            result = self._listing(request.url)
            if result:
                return result
            return ResolutionResult("fallback_text", reason="explicit link could not be resolved")
        if self.discover:
            query = self._query(request)
            self.progress("discover", query)
            outcome = self.discover.search(query) if hasattr(self.discover, "search") else self.discover(query)
            candidates = outcome.candidates if hasattr(outcome, "candidates") else outcome
            for candidate in rank_candidates(candidates, request.url):
                result = self._attempt(candidate)
                if result:
                    return result
        return ResolutionResult("needs_explicit_link", reason="automatic resolution did not find a posting")
