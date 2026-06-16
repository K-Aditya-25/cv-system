from __future__ import annotations

from typing import Any

from .refinement_routes import LocalAction, RefinementRoute, full_context_route

BOOL_FIELDS = {
    "include_coursework",
    "include_education_bullets",
    "show_experience_technologies",
    "show_project_technologies",
}


def parse_action(payload: dict[str, Any]) -> LocalAction:
    return LocalAction(
        type=str(payload.get("type") or ""),
        field=payload.get("field"),
        value=payload.get("value"),
        section=payload.get("section"),
        item_kind=payload.get("item_kind"),
        item_id=payload.get("item_id"),
    )


def validate_local_route(route: RefinementRoute, context: Any | None) -> RefinementRoute:
    if context is None or route.local_action is None:
        return route
    if local_action_valid(route.local_action, context):
        return route
    return full_context_route("local action did not validate against current CV")


def local_action_valid(action: LocalAction, context: Any) -> bool:
    if action.type == "set_job_config_field":
        return action.field in BOOL_FIELDS and isinstance(action.value, bool)
    if action.type == "remove_section":
        return isinstance(action.section, str) and action.section in _sections(context)
    if action.type == "remove_selected_item":
        return _selected_id_exists(context.selection, action.item_kind, action.item_id)
    if action.type == "remove_skill_category":
        return isinstance(action.field, str) and bool(action.field.strip())
    return False


def _sections(context: Any) -> set[str]:
    sections = set(context.job_config.sections_order or [])
    sections.update(context.selection.custom_sections)
    return sections


def _selected_id_exists(selection: Any, kind: str | None, item_id: str | None) -> bool:
    if not isinstance(kind, str) or not isinstance(item_id, str):
        return False
    values = getattr(selection, kind, None)
    if not isinstance(values, list):
        return False
    return any((getattr(item, "id", item) == item_id) for item in values)
