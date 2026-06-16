from __future__ import annotations

import os

from .block_scoring import BlockExtraction
from .boundary_planner import tensorix_boundary, trafilatura_fallback
from .description_cleaner import clean_job_description
from .extraction_quality import assess_extraction
from .job_description_filter import EMPTY_SECTION_SEQUENCES, tensorix_description_filter
from .visible_blocks import VisibleBlock

SECTION_MARKERS = (
    "what you will accomplish",
    "what you will bring",
    "responsibilities",
    "requirements",
    "qualifications",
    "recruiting process",
    "additional details",
)


def fallback_extraction(
    html: str, blocks: list[VisibleBlock], reason: str, baseline: BlockExtraction | None = None,
) -> tuple[str, BlockExtraction] | None:
    timeout = _fallback_timeout()
    filter_timeout = _filter_timeout()
    _log(f"fallback requested: {reason}; timeout={timeout:.1f}s filter_timeout={filter_timeout:.1f}s")
    for method, label, fallback in (
        (
            "job-description-filter",
            "Tensorix small LLM job-description-filter",
            lambda: tensorix_description_filter(blocks, timeout=filter_timeout),
        ),
        ("trafilatura", "trafilatura", lambda: trafilatura_fallback(html, timeout=timeout)),
        ("boundary-planner", "Tensorix boundary-planner", lambda: tensorix_boundary(blocks, timeout=timeout)),
    ):
        boundary = fallback()
        _log(f"{label} fallback result: {boundary.reason}")
        if not boundary.extraction:
            continue
        extraction = clean_block(boundary.extraction)
        report = assess_extraction(
            extraction.text, extraction.confidence, selected_blocks(blocks, extraction),
        )
        _log(f"{label} quality: {report.reason}")
        if report.usable:
            if _has_empty_section_sequence(extraction.text):
                _log(f"{label} rejected: empty job section headings without body content")
                continue
            if baseline and _loses_coverage(extraction.text, baseline.text):
                _log(f"{label} rejected: lost deterministic section coverage")
                continue
            return method, extraction
    return None


def clean_block(block: BlockExtraction) -> BlockExtraction:
    return BlockExtraction(
        clean_job_description(block.text), block.confidence, block.start, block.end, block.reason,
    )


def selected_blocks(blocks: list[VisibleBlock], block: BlockExtraction) -> list[VisibleBlock]:
    return [] if not blocks else blocks[max(block.start, 0):min(block.end + 1, len(blocks))]


def _fallback_timeout() -> float:
    try:
        return max(1.0, float(os.environ.get("JOB_EXTRACTION_FALLBACK_TIMEOUT_SECONDS", "5")))
    except ValueError:
        return 5.0


def _filter_timeout() -> float:
    try:
        configured = os.environ.get("JOBDESC_FILTER_TIMEOUT_SECONDS", "20")
        return max(5.0, float(configured))
    except ValueError:
        return 20.0


def _has_empty_section_sequence(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    return any(sequence in lowered for sequence in EMPTY_SECTION_SEQUENCES)


def _loses_coverage(candidate: str, baseline: str) -> bool:
    candidate_lower = candidate.lower()
    baseline_lower = baseline.lower()
    for marker in SECTION_MARKERS:
        if marker in baseline_lower and marker not in candidate_lower:
            return True
    baseline_words = len(baseline.split())
    candidate_words = len(candidate.split())
    return baseline_words >= 120 and candidate_words < baseline_words * 0.55


def _log(message: str) -> None:
    print(f"[resolver.extract] {message}", flush=True)
