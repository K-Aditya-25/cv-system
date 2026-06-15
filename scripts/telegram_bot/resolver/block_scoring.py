from __future__ import annotations

from dataclasses import dataclass

from .visible_blocks import VisibleBlock

JOB_TERMS = (
    "about the role", "what you will", "responsibilities", "requirements",
    "qualifications", "experience", "skills", "benefits", "recruiting process",
    "equal opportunity", "you will", "we are looking", "the team", "about the team",
    "what you bring", "what you'll do", "about us", "our mission",
)
NOISE_TERMS = (
    "sign in", "join now", "privacy policy", "cookie policy", "user agreement",
    "set alert", "show more jobs", "people also viewed", "referrals increase",
    "seniority level", "employment type", "job function", "industries",
    "direct message the job poster", "skip to main content", "show more show less",
)


@dataclass(frozen=True)
class BlockExtraction:
    text: str
    confidence: float
    start: int
    end: int
    reason: str


def extract_best_region(blocks: list[VisibleBlock]) -> BlockExtraction:
    if not blocks:
        return BlockExtraction("", 0, 0, 0, "no visible content blocks")
    scores = [_score(block) for block in blocks]
    positive = [i for i, score in enumerate(scores) if score >= 2]
    if not positive:
        index = max(range(len(blocks)), key=lambda i: scores[i])
        return _region(blocks, index, index, scores, "single best low-confidence block")
    start, end = min(positive), max(positive)
    while start > 0 and _keeps_context(blocks[start - 1], scores[start - 1]):
        start -= 1
    while end + 1 < len(blocks) and _keeps_context(blocks[end + 1], scores[end + 1]):
        end += 1
    return _region(blocks, start, end, scores, "best contiguous job-like region")


def _region(blocks: list[VisibleBlock], start: int, end: int, scores: list[float],
            reason: str) -> BlockExtraction:
    selected = [block.text for block in blocks[start:end + 1] if _score(block) > -2]
    text = "\n".join(selected).strip()
    avg_score = sum(scores[start:end + 1]) / max(end - start + 1, 1)
    confidence = min(0.95, max(0.05, 0.45 + avg_score / 10))
    return BlockExtraction(text, confidence, start, end, reason)


def _score(block: VisibleBlock) -> float:
    text = block.text.lower()
    words = len(text.split())
    score = 0.0
    if words >= 25:
        score += 2
    if words >= 80:
        score += 1
    score += sum(1.2 for term in JOB_TERMS if term in text)
    score -= sum(1.5 for term in NOISE_TERMS if term in text)
    if block.link_density > 0.35:
        score -= 3
    if words < 12:
        score -= 1
    if _looks_like_listing_card(text):
        score -= 2
    return score


def _looks_like_listing_card(text: str) -> bool:
    recency_terms = (" ago", " week", " days", " minutes", " month")
    role_terms = ("engineer", "developer", "analyst", "data", "software")
    return any(term in text for term in recency_terms) and any(term in text for term in role_terms)


def _keeps_context(block: VisibleBlock, score: float) -> bool:
    text = block.text.lower()
    if any(term in text for term in NOISE_TERMS) or block.link_density > 0.35:
        return False
    return len(text.split()) >= 8 and score > -1.5
