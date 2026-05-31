from typing import Any

from scripts.cv_generation.errors import CvGenerationError


def index_by_id(items: list[Any], section_name: str) -> dict[str, Any]:
    indexed = {item.id: item for item in items}
    if len(indexed) != len(items):
        raise CvGenerationError(f"Duplicate IDs detected in {section_name}")
    return indexed


def select_simple_items(
    selected_ids: list[str], available_items: list[Any], section_name: str,
) -> list[dict[str, Any]]:
    indexed = index_by_id(available_items, section_name)
    selected: list[dict[str, Any]] = []
    for selected_id in selected_ids:
        item = indexed.get(selected_id)
        if item is None:
            raise CvGenerationError(f"Selected {section_name} ID does not exist: {selected_id}")
        selected.append(item.model_dump())
    return selected


def select_items_with_bullets(
    selected_entries: list[Any], available_items: list[Any], section_name: str,
) -> list[dict[str, Any]]:
    indexed = index_by_id(available_items, section_name)
    selected: list[dict[str, Any]] = []
    for entry in selected_entries:
        item = indexed.get(entry.id)
        if item is None:
            raise CvGenerationError(f"Selected {section_name} ID does not exist: {entry.id}")
        item_data = item.model_dump()
        bullets_by_id = {bullet["id"]: bullet for bullet in item_data.get("bullets", [])}
        chosen_bullets = []
        for bullet_id in entry.bullets:
            bullet = bullets_by_id.get(bullet_id)
            if bullet is None:
                raise CvGenerationError(
                    f"Selected bullet '{bullet_id}' does not belong to {section_name} '{entry.id}'"
                )
            chosen_bullets.append(bullet)
        item_data["bullets"] = chosen_bullets
        selected.append(item_data)
    return selected
