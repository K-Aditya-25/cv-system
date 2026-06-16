from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin
from scripts.telegram_bot.resolver_models import ExtractedPosting, FetchedPage, JobMetadata
from .block_scoring import BlockExtraction, extract_best_region
from .description_cleaner import clean_job_description
from .extraction_fallback import clean_block, fallback_extraction, selected_blocks
from .extraction_quality import assess_extraction
from .job_description_filter import EMPTY_SECTION_SEQUENCES
from .structured_job import job_from_json_ld
from .visible_blocks import JobPageParser

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
        description = clean_job_description(structured.description)
        report = assess_extraction(description, 0.95, [])
        _log(f"json-ld candidate: {report.reason}")
        if report.usable:
            _log("using structured JobPosting JSON-LD")
            return ExtractedJob(description, structured.title,
                                structured.company, structured.location, "json-ld")
    block = clean_block(extract_best_region(parser.blocks))
    report = assess_extraction(block.text, block.confidence, selected_blocks(parser.blocks, block))
    _log(f"dom-score candidate: {report.reason}; {block.reason}; blocks={block.start}-{block.end}")
    if report.usable and not report.needs_fallback:
        if _has_empty_section_sequence(block.text):
            raise ExtractionError("extracted text has empty job section headings")
        return _block_job(block, "dom-score")
    if not report.usable:
        raise ExtractionError(report.reason)
    fallback = fallback_extraction(html, parser.blocks, report.reason, block)
    if fallback:
        method, extracted = fallback
        return _block_job(extracted, method)
    if _has_empty_section_sequence(block.text):
        raise ExtractionError("extracted text has empty job section headings")
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


def _block_job(block: BlockExtraction, method: str) -> ExtractedJob:
    _log(f"using {method} extraction; confidence={block.confidence:.2f}")
    return ExtractedJob(block.text, method=method)


def _log(message: str) -> None:
    print(f"[resolver.extract] {message}", flush=True)


def _has_empty_section_sequence(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return any(sequence in lowered for sequence in EMPTY_SECTION_SEQUENCES)
