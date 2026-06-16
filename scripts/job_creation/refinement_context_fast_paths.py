from __future__ import annotations

import re

from .refinement_routes import LOCAL_CONTEXT, LocalAction, RefinementRoute, RefinementRouteKind


def route_context_fast_path(feedback: str, context) -> RefinementRoute | None:
    target = _remove_item_target(_normalize(feedback))
    if not target:
        return None
    match = _selected_project_match(target, context)
    if not match:
        return None
    return RefinementRoute(
        RefinementRouteKind.LOCAL_EDIT,
        f"exact command to remove selected projects.{match}",
        LOCAL_CONTEXT,
        local_action=LocalAction("remove_selected_item", item_kind="projects", item_id=match),
    )


def _remove_item_target(text: str) -> str | None:
    match = re.fullmatch(r"(?:please )?(?:remove|hide|exclude) ([a-z0-9_ -]+)(?: please)?", text)
    return match.group(1) if match else None


def _selected_project_match(target: str, context) -> str | None:
    selected = {item.id for item in getattr(context.selection, "projects", [])}
    candidates = [project for project in context.database.projects if project.id in selected]
    matches = [project.id for project in candidates if _name_matches(target, project.name, project.id)]
    return matches[0] if len(matches) == 1 else None


def _name_matches(target: str, name: str, item_id: str) -> bool:
    target_tokens = set(_slug(target).split("_"))
    name_tokens = set(_slug(name).split("_"))
    return _slug(target) == _slug(item_id) or bool(target_tokens) and target_tokens <= name_tokens


def _normalize(feedback: str) -> str:
    text = re.sub(r"\s+", " ", feedback.strip().lower())
    return text.strip(" .!")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
