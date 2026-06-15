from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urljoin
from scripts.telegram_bot.resolver_models import ExtractedPosting, FetchedPage, JobMetadata
from .block_scoring import BlockExtraction, extract_best_region
from .boundary_planner import tensorix_boundary, trafilatura_fallback
from .extraction_quality import assess_extraction
from .structured_job import job_from_json_ld
from .visible_blocks import JobPageParser, VisibleBlock

class ExtractionError(ValueError): pass


@dataclass(frozen=True)
class ExtractedJob:
    description: str
    title: str = ""
    company: str = ""
    location: str = ""
    method: str = "html"


def extract_job(html: str) -> ExtractedJob:
    parser = JobPageParser()
    parser.feed(html)
    structured = job_from_json_ld(parser.scripts)
    if structured:
        report = assess_extraction(structured.description, 0.95, [])
        _log(f"json-ld candidate: {report.reason}")
        if report.usable:
            _log("using structured JobPosting JSON-LD")
            return ExtractedJob(structured.description, structured.title,
                                structured.company, structured.location, "json-ld")
    block = extract_best_region(parser.blocks)
    report = assess_extraction(block.text, block.confidence, _selected(parser.blocks, block))
    _log(f"dom-score candidate: {report.reason}; {block.reason}; blocks={block.start}-{block.end}")
    if report.usable and not report.needs_fallback:
        return _block_job(block, "dom-score")
    if not report.usable:
        raise ExtractionError(report.reason)
    fallback = _fallback(html, parser.blocks, report.reason)
    if fallback:
        method, extracted = fallback
        return _block_job(extracted, method)
    _log("fallback unavailable; accepting deterministic low-confidence extraction")
    return _block_job(block, "dom-score-low-confidence")


def extract_page(page: FetchedPage) -> ExtractedPosting:
    charset = "utf-8"
    if "charset=" in page.content_type.lower():
        charset = page.content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
    job = extract_job(page.body.decode(charset, errors="replace"))
    metadata = JobMetadata(company=job.company, role=job.title, location=job.location)
    return ExtractedPosting(job.description, metadata, page.final_url)


def listing_urls(html: str, base_url: str) -> list[str]:
    parser = JobPageParser()
    parser.feed(html)
    return [urljoin(base_url, href) for href in parser.links]


def _fallback(html: str, blocks: list[VisibleBlock], reason: str) -> tuple[str, BlockExtraction] | None:
    timeout = _fallback_timeout()
    _log(f"fallback requested: {reason}; timeout={timeout:.1f}s")
    for method, boundary in (
        ("trafilatura", trafilatura_fallback(html, timeout=timeout)),
        ("boundary-planner", tensorix_boundary(blocks, timeout=timeout)),
    ):
        _log(f"{method} fallback result: {boundary.reason}")
        if not boundary.extraction:
            continue
        selected = _selected(blocks, boundary.extraction)
        report = assess_extraction(boundary.extraction.text, boundary.extraction.confidence, selected)
        _log(f"{method} quality: {report.reason}")
        if report.usable:
            return method, boundary.extraction
    return None


def _block_job(block: BlockExtraction, method: str) -> ExtractedJob:
    _log(f"using {method} extraction; confidence={block.confidence:.2f}")
    return ExtractedJob(block.text, method=method)


def _selected(blocks: list[VisibleBlock], block: BlockExtraction) -> list[VisibleBlock]:
    return [] if not blocks else blocks[max(block.start, 0):min(block.end + 1, len(blocks))]


def _fallback_timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("JOB_EXTRACTION_FALLBACK_TIMEOUT_SECONDS", "5")))
    except ValueError: return 5.0


def _log(message: str) -> None:
    print(f"[resolver.extract] {message}", flush=True)
