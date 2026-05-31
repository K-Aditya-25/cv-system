from __future__ import annotations

import sys
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parents[1]
if str(ROOT_PATH) not in sys.path:
    sys.path.insert(0, str(ROOT_PATH))

from scripts.cv_generation.cli import main, parse_args
from scripts.cv_generation.constants import DEFAULT_PAGE_MARGIN, DEFAULT_SECTION_ORDERS, SECTION_TITLES
from scripts.cv_generation.context import build_render_context, has_section_content
from scripts.cv_generation.date_constants import CURRENT_DATE_MARKERS, MONTHS, SEASONS
from scripts.cv_generation.errors import CvGenerationError
from scripts.cv_generation.files import (
    DEFAULT_MASTER_DATA_PATH,
    ROOT,
    load_yaml,
    resolve_master_data_path,
    safe_latex_name,
)
from scripts.cv_generation.latex import LATEX_REPLACEMENTS, category_label, escape_tex, escape_url, href_url
from scripts.cv_generation.recency import parse_recency_date, recency_sort_key, sort_by_recency
from scripts.cv_generation.rendering import render_cv
from scripts.cv_generation.select_items import index_by_id, select_items_with_bullets, select_simple_items
from scripts.cv_generation.select_sections import select_custom_sections, select_skills

__all__ = [
    "CURRENT_DATE_MARKERS", "DEFAULT_MASTER_DATA_PATH", "DEFAULT_PAGE_MARGIN",
    "DEFAULT_SECTION_ORDERS", "LATEX_REPLACEMENTS", "MONTHS", "ROOT", "SEASONS", "SECTION_TITLES",
    "CvGenerationError", "build_render_context", "category_label", "escape_tex", "escape_url",
    "has_section_content", "href_url", "index_by_id", "load_yaml", "main", "parse_args",
    "parse_recency_date", "recency_sort_key", "render_cv", "resolve_master_data_path",
    "safe_latex_name", "select_custom_sections", "select_items_with_bullets", "select_simple_items",
    "select_skills", "sort_by_recency",
]

if __name__ == "__main__":
    sys.exit(main())
