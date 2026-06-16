from __future__ import annotations

import re

from .description_markers import HEADER_LINE_MARKERS, TAIL_LINE_MARKERS, TRAILING_SECTION_HEADINGS


def clean_job_description(text: str) -> str:
    lines = [_normalize_space(line) for line in text.splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return _clean_inline(text)

    kept: list[str] = []
    for line in lines:
        lowered = line.lower()
        if _is_header_noise(lowered):
            continue
        if _is_tail_noise(lowered):
            break
        kept.append(_clean_inline(line))

    cleaned = "\n".join(line for line in kept if line).strip()
    cleaned = _trim_legal_tail(cleaned)
    cleaned = _trim_trailing_headings(cleaned)
    return cleaned or _trim_trailing_headings(_trim_legal_tail(_clean_inline(text)))


def _is_header_noise(lowered: str) -> bool:
    if "see who" in lowered and "hired for this role" in lowered:
        return True
    if any(marker in lowered for marker in HEADER_LINE_MARKERS):
        return True
    is_recruiter_chrome = "recruiter" in lowered and "recruiting process" not in lowered
    return is_recruiter_chrome and len(lowered.split()) <= 14


def _is_tail_noise(lowered: str) -> bool:
    return any(marker in lowered for marker in TAIL_LINE_MARKERS)


def _clean_inline(text: str) -> str:
    cleaned = _normalize_space(text)
    cleaned = re.sub(
        r"This button displays the currently selected search type\..*?current selection\.\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bJoin to apply for the .{0,140}? role at "
        r"[A-Za-z0-9][\w&.,'’+-]*(?:\s+[A-Za-z0-9][\w&.,'’+-]*){0,5}?",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\bDirect message the job poster.{0,180}?(?=\b(?:At|About|What|Build|Contribute|"
        r"Improve|Collaborate|Strengthen|Participate|Develop|Bachelor|Master|Strong|"
        r"Proficiency|Working|Exposure|Understanding|Experience)\b)",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return _normalize_space(cleaned)


def _trim_legal_tail(text: str) -> str:
    lowered = text.lower()
    positions = [lowered.find(marker) for marker in TAIL_LINE_MARKERS if marker in lowered]
    if not positions:
        return text.strip()
    return text[:min(positions)].strip()


def _trim_trailing_headings(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        return cleaned
    heading_pattern = "|".join(re.escape(heading) for heading in TRAILING_SECTION_HEADINGS)
    while True:
        next_value = re.sub(
            rf"(?:\s*(?:{heading_pattern})\s*)+$",
            "",
            cleaned,
            flags=re.IGNORECASE,
        ).strip()
        if next_value == cleaned:
            return cleaned
        cleaned = next_value


def _normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
