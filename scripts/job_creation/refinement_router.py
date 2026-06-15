from __future__ import annotations

import os
from typing import Any

from .errors import IntakeError
from .llm import parse_llm_json
from .prompting import render_prompt_template
from .refinement_action_validation import parse_action, validate_local_route
from .refinement_fast_paths import route_fast_path
from .refinement_routes import (
    COMPACT_CONTEXT,
    LOCAL_CONTEXT,
    RefinementRoute,
    RefinementRouteKind,
    full_context_route,
)
from .refinement_router_prompt import planner_user_prompt
from .tensorix_chat import tensorix_chat

MIN_CONFIDENCE = 0.7


def route_refinement_feedback(feedback: str, context: Any | None = None) -> RefinementRoute:
    fast = route_fast_path(feedback)
    if fast is not None:
        return validate_local_route(fast, context)
    if not feedback.strip() or os.environ.get("CV_ROUTER_ENABLED", "1") == "0":
        return full_context_route("router disabled or empty feedback")
    if context is None:
        return full_context_route("router context unavailable")
    try:
        return _route_with_planner(feedback, context)
    except IntakeError as exc:
        return full_context_route(f"router planner unavailable: {exc}")


def _route_with_planner(feedback: str, context: Any) -> RefinementRoute:
    raw = tensorix_chat(
        render_prompt_template("refinement_router_system.md"),
        planner_user_prompt(feedback, context),
    )
    payload = parse_llm_json(raw)
    route = str(payload.get("route") or "")
    confidence = _confidence(payload)
    if confidence < _min_confidence():
        return full_context_route("router confidence below threshold", confidence)
    if route == "compact_refinement":
        return RefinementRoute(
            RefinementRouteKind.COMPACT_REFINEMENT,
            str(payload.get("reason") or "planner selected compact context"),
            COMPACT_CONTEXT,
            confidence,
        )
    if route == "local_edit":
        return _local_route(payload, context, confidence)
    if route == "full_context_refinement":
        return full_context_route(str(payload.get("reason") or "planner selected full context"), confidence)
    return full_context_route("router returned an unknown route", confidence)


def _local_route(payload: dict[str, Any], context: Any, confidence: float) -> RefinementRoute:
    action_payload = payload.get("local_action")
    if not isinstance(action_payload, dict):
        return full_context_route("router local action was missing", confidence)
    action = parse_action(action_payload)
    route = RefinementRoute(
        RefinementRouteKind.LOCAL_EDIT,
        str(payload.get("reason") or "planner selected local edit"),
        LOCAL_CONTEXT,
        confidence,
        action,
    )
    return validate_local_route(route, context)


def _confidence(payload: dict[str, Any]) -> float:
    try:
        return float(payload.get("confidence", 0))
    except (TypeError, ValueError):
        return 0.0


def _min_confidence() -> float:
    try:
        return float(os.environ.get("CV_ROUTER_MIN_CONFIDENCE", MIN_CONFIDENCE))
    except ValueError:
        return MIN_CONFIDENCE
