from __future__ import annotations

from dataclasses import dataclass

from .visible_blocks import VisibleBlock


@dataclass(frozen=True)
class QualityReport:
    usable: bool
    needs_fallback: bool
    reason: str


def assess_extraction(text: str, confidence: float, blocks: list[VisibleBlock]) -> QualityReport:
    words = len(text.split())
    if words < 40:
        return QualityReport(False, True, "extracted text is too short")
    lowered = text.lower()
    blocked = ("captcha", "verify you are human", "sign in to continue", "log in to continue")
    if any(marker in lowered for marker in blocked):
        return QualityReport(False, True, "page appears blocked or gated")
    if confidence < 0.62:
        return QualityReport(True, True, f"low deterministic confidence {confidence:.2f}")
    if _contaminated(text, blocks):
        return QualityReport(True, True, "extracted text looks contaminated by listings or chrome")
    return QualityReport(True, False, f"deterministic confidence {confidence:.2f}")


def _contaminated(text: str, blocks: list[VisibleBlock]) -> bool:
    lowered = text.lower()
    noise_hits = sum(
        lowered.count(marker)
        for marker in ("similar jobs", "people also viewed", "privacy policy", "user agreement")
    )
    link_heavy = sum(1 for block in blocks if block.link_density > 0.35)
    return noise_hits >= 2 or link_heavy > max(3, len(blocks) // 3)
