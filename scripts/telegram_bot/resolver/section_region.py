from __future__ import annotations

from .description_markers import TAIL_LINE_MARKERS
from .job_section_markers import is_job_section_anchor, keeps_visible_text_block
from .visible_blocks import VisibleBlock

STOP_MARKERS = TAIL_LINE_MARKERS + (
    "apply now",
    "save job",
    "jobs you may be interested in",
    "recommended jobs",
)


def expand_job_section_region(
    blocks: list[VisibleBlock], start: int, end: int
) -> tuple[int, int]:
    if not any(is_job_section_anchor(blocks[i].text) for i in range(start, end + 1)):
        return start, end
    while start > 0 and _keeps_section_context(blocks[start - 1]):
        start -= 1
    while end + 1 < len(blocks) and _keeps_section_context(blocks[end + 1]):
        end += 1
    return start, end


def _keeps_section_context(block: VisibleBlock) -> bool:
    text = block.text.lower()
    if block.link_density > 0.35:
        return False
    if any(marker in text for marker in STOP_MARKERS):
        return False
    return keeps_visible_text_block(block.text)
