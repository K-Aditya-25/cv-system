import re
from calendar import monthrange
from typing import Any

from scripts.cv_generation.date_constants import CURRENT_DATE_MARKERS, MONTHS, SEASONS
from scripts.cv_generation.errors import CvGenerationError


def parse_recency_date(value: Any) -> tuple[int, int, int] | None:
    if value is None or not (text := str(value).strip()):
        return None
    normalized = re.sub(r"\s+", " ", text.lower())
    if normalized in CURRENT_DATE_MARKERS:
        return (9999, 12, 31)
    if re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", normalized):
        year_text, month_text, day_text = normalized.split("-")
        year, month, day = int(year_text), int(month_text), int(day_text)
        if 1 <= month <= 12 and 1 <= day <= monthrange(year, month)[1]:
            return (year, month, day)
        return None
    if re.fullmatch(r"\d{4}-\d{1,2}", normalized):
        year, month = (int(part) for part in normalized.split("-"))
        return (year, month, monthrange(year, month)[1]) if 1 <= month <= 12 else None
    month_year = re.fullmatch(r"([a-z]+)\.?\s+(\d{4})|(\d{4})\s+([a-z]+)\.?", normalized)
    if month_year:
        month_name = month_year.group(1) or month_year.group(4)
        year = int(month_year.group(2) or month_year.group(3))
        if month := MONTHS.get(month_name):
            return (year, month, monthrange(year, month)[1])
    season_year = re.fullmatch(r"([a-z]+)\s+(\d{4})", normalized)
    if season_year and (season := SEASONS.get(season_year.group(1))):
        year = int(season_year.group(2))
        return (year, season, monthrange(year, season)[1])
    if re.fullmatch(r"\d{4}", normalized):
        return (int(normalized), 12, 31)
    if years := re.findall(r"\b(19\d{2}|20\d{2}|21\d{2})\b", normalized):
        return (max(int(year) for year in years), 12, 31)
    return None


def recency_sort_key(
    item: dict[str, Any], section_name: str,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    if section_name == "experience":
        primary, secondary = parse_recency_date(item.get("end_date")), parse_recency_date(item.get("start_date"))
    elif section_name == "projects":
        primary, secondary = parse_recency_date(item.get("date")), None
    else:
        raise CvGenerationError(f"Unsupported recency-sorted section: {section_name}")
    unknown = (0, 0, 0)
    return primary or unknown, secondary or unknown


def sort_by_recency(items: list[dict[str, Any]], section_name: str) -> list[dict[str, Any]]:
    return sorted(items, key=lambda item: recency_sort_key(item, section_name), reverse=True)
