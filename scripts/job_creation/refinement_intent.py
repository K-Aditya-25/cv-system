from __future__ import annotations

import re

EVIDENCE_NOUNS = (
    "project", "projects", "experience", "experiences", "skill", "skills",
    "achievement", "achievements", "certification", "certifications",
    "volunteering", "leadership", "bullet", "bullets",
)

EDIT_VERBS = r"\b(?:add|include|replace|swap|remove|drop|exclude|change|select|use)\b"
FOCUS_VERBS = r"\b(?:focus|emphasize|emphasise|prioritize|prioritise|tailor|match)\b"


def requires_full_context(feedback: str) -> bool:
    text = re.sub(r"\s+", " ", feedback.strip().lower())
    if not text:
        return False
    evidence_pattern = r"\b(?:" + "|".join(EVIDENCE_NOUNS) + r")\b"
    if re.search(EDIT_VERBS + r".{0,80}" + evidence_pattern, text):
        return True
    if re.search(evidence_pattern + r".{0,80}" + EDIT_VERBS, text):
        return True
    return bool(re.search(FOCUS_VERBS, text) and re.search(evidence_pattern, text))
