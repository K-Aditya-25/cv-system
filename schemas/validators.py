def find_duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates


def ensure_unique_ids(items: list[object], section_name: str) -> None:
    ids = [getattr(item, "id") for item in items]
    duplicates = find_duplicates(ids)
    if duplicates:
        raise ValueError(f"{section_name} has duplicate IDs: {', '.join(duplicates)}")
