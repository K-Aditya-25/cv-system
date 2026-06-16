from __future__ import annotations

import os

from .block_scoring import extract_best_region
from .description_cleaner import clean_job_description
from .extract import ExtractedJob, ExtractionError, _has_empty_section_sequence
from .extraction_fallback import clean_block, selected_blocks
from .extraction_quality import assess_extraction
from .job_description_filter import tensorix_description_filter
from .structured_job import job_from_json_ld
from .visible_blocks import JobPageParser


def extract_linkedin_fast(html: str, *, allow_llm: bool = True) -> ExtractedJob:
    parser = JobPageParser()
    parser.feed(html)
    structured = job_from_json_ld(parser.scripts)
    if structured:
        description = clean_job_description(structured.description)
        report = assess_extraction(description, 0.95, [])
        if report.usable:
            return ExtractedJob(description, structured.title, structured.company,
                                structured.location, "json-ld")
    block = clean_block(extract_best_region(parser.blocks))
    report = assess_extraction(block.text, block.confidence, selected_blocks(parser.blocks, block))
    if _accepts_deterministic(block.text, report):
        return ExtractedJob(block.text, method="dom-score")
    if not allow_llm:
        raise ExtractionError(report.reason)
    boundary = tensorix_description_filter(parser.blocks, timeout=_timeout())
    if boundary.extraction:
        cleaned = clean_block(boundary.extraction)
        quality = assess_extraction(cleaned.text, cleaned.confidence, [])
        if quality.usable and not _has_empty_section_sequence(cleaned.text):
            return ExtractedJob(cleaned.text, method="tensorix-small-llm")
    raise ExtractionError(boundary.reason or report.reason)


def _timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("JOBDESC_FILTER_TIMEOUT_SECONDS", "8")))
    except ValueError:
        return 8.0


def _accepts_deterministic(text: str, report) -> bool:
    lowered = text.lower()
    if not report.usable or _has_empty_section_sequence(text):
        return False
    if any(marker in lowered for marker in ("similar jobs", "people also viewed", "seniority level")):
        return False
    has_section = "what you will accomplish" in lowered or "what you will bring" in lowered
    return not report.needs_fallback or has_section and len(text.split()) >= 60
