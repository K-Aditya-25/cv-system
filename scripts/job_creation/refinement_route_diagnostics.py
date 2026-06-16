from __future__ import annotations

from typing import Any

from .refinement_routes import RefinementRoute, RefinementRouteKind


def route_diagnostics(route: RefinementRoute) -> dict[str, Any]:
    data: dict[str, Any] = {
        "route": route.kind.value,
        "reason": route.reason,
        "confidence": route.confidence,
        "required_context": list(route.required_context),
        "claude_required": route.kind != RefinementRouteKind.LOCAL_EDIT,
    }
    if route.local_action:
        data["local_action"] = {
            "type": route.local_action.type,
            "field": route.local_action.field,
            "value": route.local_action.value,
            "section": route.local_action.section,
            "item_kind": route.local_action.item_kind,
            "item_id": route.local_action.item_id,
        }
    return data


def format_route_log(route: RefinementRoute) -> str:
    data = route_diagnostics(route)
    parts = [
        f"route={data['route']}",
        f"reason={_quote(data['reason'])}",
        f"claude_required={str(data['claude_required']).lower()}",
        "context=" + ",".join(data["required_context"]),
    ]
    action = data.get("local_action")
    if action:
        parts.append(f"action={action['type']}")
        parts.extend(
            f"{key}={value}"
            for key, value in action.items()
            if key != "type" and value is not None
        )
    return "[refinement.route] " + " ".join(parts)


def format_route_cli(route: RefinementRoute) -> str:
    data = route_diagnostics(route)
    lines = [
        f"route: {data['route']}",
        f"reason: {data['reason']}",
        f"confidence: {data['confidence']}",
        f"claude_required: {str(data['claude_required']).lower()}",
        "required_context:",
    ]
    lines.extend(f"- {item}" for item in data["required_context"])
    action = data.get("local_action")
    if action:
        lines.append("local_action:")
        lines.extend(
            f"  {key}: {value}"
            for key, value in action.items()
            if value is not None
        )
    return "\n".join(lines)


def _quote(value: Any) -> str:
    return '"' + str(value).replace('"', '\\"') + '"'
