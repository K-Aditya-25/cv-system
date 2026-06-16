from __future__ import annotations

import re

SECTION_ANCHORS = (
    "about the job",
    "about the role",
    "about the team",
    "what you will accomplish",
    "what you will bring",
    "what you bring",
    "what you'll do",
    "responsibilities",
    "requirements",
    "qualifications",
    "recruiting process",
    "additional details",
)

SHORT_JOB_LINES = (
    "coding assessment",
    "technical interview",
    "onsite interview",
    "phone interview",
    "recruiter screen",
    "manager interview",
)


def is_job_section_anchor(text: str) -> bool:
    normalized = _normalize(text)
    return any(normalized == item or normalized.startswith(f"{item} ") for item in SECTION_ANCHORS)


def keeps_visible_text_block(text: str) -> bool:
    normalized = _normalize(text)
    words = normalized.split()
    if len(words) >= 4:
        return True
    if is_job_section_anchor(normalized) or normalized in SHORT_JOB_LINES:
        return True
    if 2 <= len(words) <= 4 and words[-1] in {"assessment", "interview"}:
        return True
    return False


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()
