from __future__ import annotations

import os
import re

from scripts.job_creation.llm import parse_llm_json
from scripts.job_creation.tensorix_chat import DEFAULT_ROUTER_MODEL, tensorix_chat
from .block_scoring import BlockExtraction
from .boundary_planner import PlannedBoundary
from .description_cleaner import clean_job_description
from .html_text import html_to_text
from .job_description_filter_prompt import system_prompt, user_prompt
from .visible_blocks import VisibleBlock

DEFAULT_FILTER_MODEL = DEFAULT_ROUTER_MODEL
DEFAULT_MAX_TOKENS = 3000
MAX_INPUT_CHARS = 60000
EMPTY_SECTION_SEQUENCES = (
    "what you will accomplish what you will bring",
    "what you will bring recruiting process",
    "recruiting process additional details",
)
NOISE_MARKERS = (
    "similar jobs", "people also viewed", "seniority level", "employment type",
    "job function", "engineering and information technology",
    "technology, information and internet",
)


def tensorix_description_filter(blocks: list[VisibleBlock], timeout: float = 10) -> PlannedBoundary:
    if os.environ.get("JOB_DESCRIPTION_FILTER_ENABLED", "1") == "0":
        return PlannedBoundary(None, "Tensorix job-description filter disabled")
    model = os.environ.get("JOBDESC_FILTER_MODEL", DEFAULT_FILTER_MODEL)
    source = _source_text(blocks)
    if len(source.split()) < 40:
        return PlannedBoundary(None, "not enough visible page text for Tensorix filter")
    try:
        raw = tensorix_chat(
            system_prompt(), user_prompt(source), timeout,
            model=model,
            max_tokens=_max_tokens(),
            response_format={"type": "json_object"},
        )
        data = parse_llm_json(raw)
    except Exception as exc:
        reason = f"Tensorix job-description filter unavailable using model {model}: {exc}"
        return PlannedBoundary(None, reason)
    extraction = _from_payload(data, blocks)
    if not extraction:
        return PlannedBoundary(None, "Tensorix job-description filter returned unusable text")
    reason = f"model={model}; {data.get('reason') or 'Tensorix filtered noisy page text'}"
    return PlannedBoundary(extraction, reason)


def _from_payload(data: dict, blocks: list[VisibleBlock]) -> BlockExtraction | None:
    text = clean_job_description(html_to_text(str(data.get("job_description") or "")))
    try:
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        confidence = 0
    if confidence < 0.65 or not _usable(text):
        return None
    return BlockExtraction(text, confidence, 0, 0, "Tensorix job-description filter")


def _usable(text: str) -> bool:
    lowered = re.sub(r"\s+", " ", text.lower()).strip()
    if len(lowered.split()) < 60:
        return False
    if any(sequence in lowered for sequence in EMPTY_SECTION_SEQUENCES):
        return False
    return not any(marker in lowered for marker in NOISE_MARKERS)


def _source_text(blocks: list[VisibleBlock]) -> str:
    lines = [f"[{block.index}] {block.text}" for block in blocks]
    text = "\n".join(lines).strip()
    return text[:MAX_INPUT_CHARS]


def _max_tokens() -> int:
    try:
        return max(1000, int(os.environ.get("JOBDESC_FILTER_MAX_TOKENS", DEFAULT_MAX_TOKENS)))
    except ValueError:
        return DEFAULT_MAX_TOKENS
