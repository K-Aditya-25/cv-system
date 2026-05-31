import copy
from typing import Any

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.cv_generation.constants import DEFAULT_PAGE_MARGIN, DEFAULT_SECTION_ORDERS, SECTION_TITLES
from scripts.cv_generation.recency import sort_by_recency
from scripts.cv_generation.select_items import select_items_with_bullets, select_simple_items
from scripts.cv_generation.select_sections import select_custom_sections, select_skills


def has_section_content(section_key: str, context: dict[str, Any]) -> bool:
    if section_key == "profile":
        return bool(context["profile"].get("summary"))
    if section_key in {"skills", "technical_skills"}:
        return bool(context.get("skills"))
    if section_key in context.get("custom_sections", {}):
        return bool(context["custom_sections"][section_key].get("items"))
    return bool(context.get(section_key))


def build_render_context(
    database: CareerDatabase, job_config: JobConfig, selection: Selection,
) -> dict[str, Any]:
    data = copy.deepcopy(database)
    context: dict[str, Any] = {
        "profile": data.profile.model_dump(),
        "job": job_config.model_dump(),
        "education": select_simple_items(selection.education, data.education, "education"),
        "experience": sort_by_recency(
            select_items_with_bullets(selection.experience, data.experience, "experience"),
            "experience",
        ),
        "projects": sort_by_recency(
            select_items_with_bullets(selection.projects, data.projects, "projects"), "projects",
        ),
        "skills": select_skills(selection.skills, data.skills),
        "volunteering": select_simple_items(selection.volunteering, data.volunteering, "volunteering"),
        "leadership": select_simple_items(selection.leadership, data.leadership, "leadership"),
        "achievements": select_simple_items(selection.achievements, data.achievements, "achievements"),
        "certifications": select_simple_items(
            selection.certifications, data.certifications, "certifications",
        ),
        "custom_sections": select_custom_sections(selection.custom_sections, data.custom_sections),
    }
    section_order = job_config.sections_order or DEFAULT_SECTION_ORDERS[job_config.cv_variant]
    context["sections_order"] = [
        section for section in section_order if has_section_content(section, context)
    ]
    context["section_titles"] = dict(SECTION_TITLES)
    for key, section in context["custom_sections"].items():
        context["section_titles"][key] = section["title"]
    context["default_page_margin"] = DEFAULT_PAGE_MARGIN
    return context
