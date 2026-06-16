from __future__ import annotations

import time

from scripts.telegram_bot.resolver_models import ExtractedPosting, JobMetadata, ResolutionResult
from .extract import ExtractionError
from .fetch import FetchError
from .linkedin import discovery_query, linkedin_job_id, rank_candidates, same_job_urls_from_html
from .linkedin_fast_extract import extract_linkedin_fast


def resolve_linkedin(service, request) -> ResolutionResult:
    job_id = linkedin_job_id(request.url) or ""
    _log(f"request_id={request.request_id} source=telegram_url strategy=linkedin_fast_pipeline "
         f"url={request.url}")
    result, links = _attempt(service, request.url, "direct_http", allow_llm=False, job_id=job_id)
    if result:
        return result
    for link in [item for item in links if item != request.url][:1]:
        result, _links = _attempt(service, link, "direct_same_job_link", job_id=job_id)
        if result:
            return result
    if service.discover:
        query = discovery_query(request.url, job_id)
        service.progress("linkedin_discover", query)
        ranked = _discover(service, query, request.url, job_id)
        if ranked:
            result, _links = _attempt(service, ranked[0], "discovered_top", job_id=job_id)
            if result:
                return result
    _log("decision=manual_required reason=no_fast_reliable_description")
    return ResolutionResult("needs_explicit_link", reason="No fast reliable LinkedIn description found.")


def _attempt(
    service, url: str, pathway: str, *, allow_llm: bool = True, job_id: str = ""
) -> tuple[ResolutionResult | None, list[str]]:
    cached = service.cache.get(url)
    if cached:
        _log(f"decision=cache_hit pathway={pathway} url={url}")
        return cached, []
    start = time.perf_counter()
    links: list[str] = []
    try:
        page = service._page(url)
        elapsed = int((time.perf_counter() - start) * 1000)
        _log(f"step=fetch pathway={pathway} status=ok elapsed_ms={elapsed} url={url}")
        html = page.body.decode(_charset(page.content_type), errors="replace")
        links = same_job_urls_from_html(html, page.final_url, job_id) if job_id else []
        _log(f"step=acquire pathway={pathway} same_job_links={len(links)}")
        job = extract_linkedin_fast(html, allow_llm=allow_llm)
        metadata = JobMetadata(company=job.company, role=job.title, location=job.location)
        posting = ExtractedPosting(job.description, metadata, page.final_url)
        result = ResolutionResult("resolved", posting=posting, metadata=metadata)
        service._store(url, page.final_url, posting.canonical_url, result)
        words = len(job.description.split())
        _log(f"step=filter method={job.method} words={words} final_url={page.final_url}")
        _log(f"decision=resolved method={job.method} final_url={page.final_url}")
        return result, links
    except (FetchError, ExtractionError, ValueError, OSError) as exc:
        elapsed = int((time.perf_counter() - start) * 1000)
        _log(f"step=fetch pathway={pathway} status=failed elapsed_ms={elapsed} url={url} reason={exc}")
        return None, links


def _discover(service, query: str, source_url: str, job_id: str) -> list[str]:
    outcome = service.discover.search(query) if hasattr(service.discover, "search") else service.discover(query)
    candidates = outcome.candidates if hasattr(outcome, "candidates") else outcome
    ranked = rank_candidates(candidates, source_url, job_id)
    top = ranked[0] if ranked else ""
    _log(f"step=discovery raw_candidates={len(candidates)} same_job_candidates={len(ranked)} top_url={top}")
    return ranked[:1]


def _charset(content_type: str) -> str:
    lowered = content_type.lower()
    if "charset=" in lowered:
        return lowered.split("charset=", 1)[1].split(";", 1)[0].strip()
    return "utf-8"


def _log(message: str) -> None:
    print(f"[resolver.route] {message}", flush=True)
