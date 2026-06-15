from __future__ import annotations

import concurrent.futures
import os
from dataclasses import dataclass

from scripts.job_creation.llm import parse_llm_json
from scripts.job_creation.tensorix_chat import tensorix_chat
from .block_scoring import BlockExtraction
from .visible_blocks import VisibleBlock


@dataclass(frozen=True)
class PlannedBoundary:
    extraction: BlockExtraction | None
    reason: str


def trafilatura_fallback(html: str, timeout: float = 5) -> PlannedBoundary:
    try:
        import trafilatura  # type: ignore
    except ImportError:
        return PlannedBoundary(None, "trafilatura is not installed")
    try:
        text = _run_with_timeout(
            lambda: trafilatura.extract(html, include_comments=False, include_tables=False),
            timeout,
        )
    except _TimedOut:
        return PlannedBoundary(None, "trafilatura extraction timed out")
    if not text or len(text.split()) < 40:
        return PlannedBoundary(None, "trafilatura returned unusable text")
    return PlannedBoundary(BlockExtraction(text.strip(), 0.7, 0, 0, "trafilatura fallback"),
                           "trafilatura extracted usable text")


def tensorix_boundary(blocks: list[VisibleBlock], timeout: float = 5) -> PlannedBoundary:
    if os.environ.get("JOB_BOUNDARY_PLANNER_ENABLED", "1") == "0":
        return PlannedBoundary(None, "Tensorix boundary planner disabled")
    prompt = _prompt(blocks)
    try:
        raw = _run_with_timeout(lambda: tensorix_chat(_system_prompt(), prompt, timeout), timeout)
        data = parse_llm_json(raw)
    except _TimedOut:
        return PlannedBoundary(None, "Tensorix boundary planner timed out")
    except Exception as exc:
        return PlannedBoundary(None, f"Tensorix boundary planner unavailable: {exc}")
    return _boundary_from_payload(blocks, data)


def _boundary_from_payload(blocks: list[VisibleBlock], data: dict) -> PlannedBoundary:
    try:
        start, end = int(data["start_block"]), int(data["end_block"])
        confidence = float(data.get("confidence", 0))
    except (KeyError, TypeError, ValueError):
        return PlannedBoundary(None, "Tensorix boundary payload was invalid")
    if confidence < 0.65 or start < 0 or end < start or end >= len(blocks):
        return PlannedBoundary(None, "Tensorix boundary confidence or indices invalid")
    text = "\n".join(block.text for block in blocks[start:end + 1]).strip()
    return PlannedBoundary(BlockExtraction(text, confidence, start, end, "Tensorix boundary planner"),
                           str(data.get("reason") or "Tensorix selected boundaries"))


def _prompt(blocks: list[VisibleBlock]) -> str:
    lines = ["Return JSON: {\"start_block\":0,\"end_block\":0,\"confidence\":0.0,\"reason\":\"...\"}"]
    for block in blocks[:80]:
        excerpt = block.text[:350].replace("\n", " ")
        lines.append(f"[{block.index}] tag={block.tag} link_density={block.link_density:.2f} {excerpt}")
    return "\n".join(lines)


def _system_prompt() -> str:
    return (
        "Select the contiguous block range containing only the actual job description. "
        "Exclude navigation, sign-in prompts, related jobs, alerts, footer links, and repeated job cards. "
        "If uncertain, return low confidence. Return JSON only."
    )


class _TimedOut(Exception):
    pass


def _run_with_timeout(call, timeout: float):
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(call)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError as exc:
        future.cancel()
        raise _TimedOut from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
