from __future__ import annotations

from typing import Any


def compact_bullets(items: list[Any]) -> list[dict[str, Any]]:
    compacted = []
    for item in items:
        item_data = item.model_dump()
        compacted.append(
            {
                "id": item_data["id"],
                "title": item_data.get("title")
                or item_data.get("name")
                or item_data.get("role")
                or item_data.get("degree"),
                "organization": item_data.get("company")
                or item_data.get("institution")
                or item_data.get("organization"),
                "start_date": item_data.get("start_date"),
                "end_date": item_data.get("end_date"),
                "date": item_data.get("date"),
                "summary": item_data.get("summary") or item_data.get("description"),
                "technologies": item_data.get("technologies", []),
                "links": item_data.get("links", []),
                "bullets": [
                    {
                        "id": bullet["id"],
                        "text": bullet["text"],
                        "tags": bullet.get("tags", []),
                        "strength": bullet.get("strength"),
                    }
                    for bullet in item_data.get("bullets", [])
                ],
            }
        )
    return compacted
