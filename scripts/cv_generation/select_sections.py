from typing import Any

from scripts.cv_generation.errors import CvGenerationError


def select_skills(
    selected_skills: dict[str, list[str]], available_skills: dict[str, list[str]],
) -> dict[str, list[str]]:
    selected: dict[str, list[str]] = {}
    for category, skills in selected_skills.items():
        if category not in available_skills:
            raise CvGenerationError(f"Selected skills category does not exist: {category}")
        missing = [skill for skill in skills if skill not in set(available_skills[category])]
        if missing:
            raise CvGenerationError(
                f"Selected skill(s) do not exist in '{category}': {', '.join(missing)}"
            )
        selected[category] = skills
    return selected


def select_custom_sections(
    selected_sections: dict[str, list[str]], available_sections: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for section_key, selected_ids in selected_sections.items():
        section = available_sections.get(section_key)
        if section is None:
            raise CvGenerationError(f"Selected custom section does not exist: {section_key}")
        item_index = {item.id: item for item in section.items}
        selected_items = []
        for selected_id in selected_ids:
            item = item_index.get(selected_id)
            if item is None:
                raise CvGenerationError(
                    f"Selected custom section item '{selected_id}' does not exist in '{section_key}'"
                )
            selected_items.append(item.model_dump())
        selected[section_key] = {"title": section.title, "items": selected_items}
    return selected
