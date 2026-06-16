from __future__ import annotations

import re

from .refinement_routes import (
    LOCAL_CONTEXT,
    LocalAction,
    RefinementRoute,
    RefinementRouteKind,
)

_FIELD_COMMANDS = (
    ("coursework", "include_coursework"),
    ("education bullets?", "include_education_bullets"),
    ("experience technolog(?:y|ies)", "show_experience_technologies"),
    ("project technolog(?:y|ies)", "show_project_technologies"),
)


def route_fast_path(feedback: str) -> RefinementRoute | None:
    text = _normalize(feedback)
    for label, field in _FIELD_COMMANDS:
        shown = _exact(text, rf"(show|include|enable) {label}")
        hidden = _exact(text, rf"(hide|remove|exclude|disable) {label}")
        if shown or hidden:
            return _local(
                f"exact command for job_config.{field}",
                LocalAction("set_job_config_field", field=field, value=bool(shown)),
            )
    if _exact(text, r"(remove|hide|exclude) additional[_ ]information"):
        return _local(
            "exact command to remove additional_information",
            LocalAction("remove_section", section="additional_information"),
        )
    skill_category = _skill_category_removal(text)
    if skill_category:
        return _local(
            f"exact command to remove skills.{skill_category}",
            LocalAction("remove_skill_category", field=skill_category),
        )
    return None


def _normalize(feedback: str) -> str:
    text = re.sub(r"\s+", " ", feedback.strip().lower())
    return text.strip(" .!")


def _exact(text: str, pattern: str) -> bool:
    polite = r"(please )?"
    return bool(re.fullmatch(polite + pattern + r"( please)?", text))


def _skill_category_removal(text: str) -> str | None:
    match = re.fullmatch(
        r"(?:please )?(?:remove|hide|exclude) ([a-z0-9_ -]+) from skills(?: please)?",
        text,
    )
    if not match:
        return None
    return re.sub(r"[^a-z0-9]+", "_", match.group(1)).strip("_")


def _local(reason: str, action: LocalAction) -> RefinementRoute:
    return RefinementRoute(
        RefinementRouteKind.LOCAL_EDIT,
        reason,
        LOCAL_CONTEXT,
        local_action=action,
    )
