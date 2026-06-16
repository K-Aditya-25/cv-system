from __future__ import annotations
from scripts.telegram_bot.resolver_models import (
    ExtractedPosting, FetchedPage, JobMetadata, ResolutionRequest, ResolutionResult,
)
from .discovery import DiscoveryService
from .extract import ExtractionError, extract_page
from .fetch import FetchError, fetch_html
from .generic_flow import resolve_generic
from .linkedin import is_linkedin_job_url
from .linkedin_flow import resolve_linkedin
from .security import validate_public_https_url

_CACHE: dict[str, ResolutionResult] = {}


class ResolverService:
    def __init__(self, *, fetch=fetch_html, extract=extract_page, browser=None, discover=None,
                 validate=validate_public_https_url, progress=None, cache=None) -> None:
        self.fetch = fetch
        self.extract = extract
        self.browser = browser
        self.discover = DiscoveryService() if discover is None else discover
        self.validate = validate
        self.progress = progress or (lambda _stage, _url: None)
        self.cache = _CACHE if cache is None else cache

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
        cached = self.cache.get(url)
        if cached:
            _log(f"cache hit for {url}")
            return cached
        self.progress("render" if rendered else "fetch", url)
        try:
            page = self._page(url, rendered)
            cached = self.cache.get(page.final_url)
            if cached:
                _log(f"cache hit for final URL {page.final_url}")
                return cached
            posting = self.extract(page)
            if not isinstance(posting, ExtractedPosting):
                metadata = JobMetadata(company=posting.company, role=posting.title,
                                       location=posting.location)
                posting = ExtractedPosting(posting.description, metadata, page.final_url)
            result = ResolutionResult("resolved", posting=posting, metadata=posting.metadata)
            self._store(url, page.final_url, posting.canonical_url, result)
            return result
        except (FetchError, ExtractionError, ValueError, OSError) as exc:
            _log(f"{'render' if rendered else 'fetch'} attempt failed for {url}: {exc}")
            return None

    def resolve(self, request: ResolutionRequest) -> ResolutionResult:
        if request.mode == "automatic" and is_linkedin_job_url(request.url):
            return resolve_linkedin(self, request)
        return resolve_generic(self, request)

    def _store(self, requested: str, final_url: str, canonical: str, result: ResolutionResult) -> None:
        for key in {requested, final_url, canonical}:
            if key:
                self.cache[key] = result
        _log(f"cached extraction for {final_url}")


def _log(message: str) -> None:
    print(f"[resolver.service] {message}", flush=True)
