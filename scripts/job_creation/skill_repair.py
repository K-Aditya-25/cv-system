from __future__ import annotations

from typing import Any

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.generate_cv import CvGenerationError, build_render_context
from .errors import IntakeError
from .validation_core import validate_intake_payload

def skill_categories_by_name(database: CareerDatabase) -> dict[str, list[str]]:
    categories: dict[str, list[str]] = {}
    for category, skills in database.skills.items():
        for skill in skills:
            categories.setdefault(skill, []).append(category)
    return categories


def append_selected_skill(
    selected_skills: dict[str, list[str]],
    category: str,
    skill: str,
) -> None:
    selected_skills.setdefault(category, [])
    if skill not in selected_skills[category]:
        selected_skills[category].append(skill)


def repair_selected_skill_categories(
    payload: dict[str, Any],
    database: CareerDatabase,
) -> list[str]:
    selection_payload = payload.get("selection")
    if not isinstance(selection_payload, dict):
        return []

    selected_skills = selection_payload.get("skills")
    if not isinstance(selected_skills, dict):
        return []

    categories_by_skill = skill_categories_by_name(database)
    repaired_skills: dict[str, list[str]] = {}
    repairs: list[str] = []

    for selected_category, skills in selected_skills.items():
        if not isinstance(skills, list):
            append_selected_skill(repaired_skills, selected_category, skills)
            continue

        for skill in skills:
            if (
                isinstance(skill, str)
                and selected_category in database.skills
                and skill in database.skills[selected_category]
            ):
                append_selected_skill(repaired_skills, selected_category, skill)
                continue

            canonical_categories = categories_by_skill.get(skill) if isinstance(skill, str) else None
            if canonical_categories:
                canonical_category = canonical_categories[0]
                append_selected_skill(repaired_skills, canonical_category, skill)
                repairs.append(f"{skill}: {selected_category} -> {canonical_category}")
                continue

            append_selected_skill(repaired_skills, selected_category, skill)

    selection_payload["skills"] = repaired_skills
    return repairs


def validate_repaired_intake_payload(
    payload: dict[str, Any],
    database: CareerDatabase,
    *,
    allow_longer_cv: bool,
) -> tuple[JobConfig, Selection, list[str]]:
    repairs = repair_selected_skill_categories(payload, database)
    job_config, selection = validate_intake_payload(payload, allow_longer_cv=allow_longer_cv)
    try:
        build_render_context(database, job_config, selection)
    except CvGenerationError as exc:
        raise IntakeError(f"Generated job config or selection failed render validation:\n{exc}") from exc
    return job_config, selection, repairs

