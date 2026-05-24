from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.job_creation.cv_output import compile_pdf, compile_pdf_and_count_pages, count_pdf_pages, generate_cv, pdf_path_for_tex
from scripts.job_creation.errors import IntakeError, InteractiveQuit
from scripts.job_creation.llm import call_anthropic
from scripts.job_creation.main import main
from scripts.job_creation.page_fit import build_one_page_enforcement_feedback, compact_page_margin, halve_margin, remove_additional_information_section
from scripts.job_creation.skill_repair import repair_selected_skill_categories
from scripts.job_creation.validation_core import selected_projects_without_portfolio_links


def call_claude_for_valid_payload(**kwargs: Any) -> tuple[Any, Any, Any, list[str]]:
    import scripts.job_creation.claude_payload as claude_payload

    claude_payload.call_anthropic = call_anthropic
    return claude_payload.call_claude_for_valid_payload(**kwargs)

def assert_pdf_is_exactly_one_page(pdf_path: Path) -> int:
    from scripts.job_creation.constants import ONE_PAGE_LIMIT

    page_count = count_pdf_pages(pdf_path)
    if page_count != ONE_PAGE_LIMIT:
        raise IntakeError(f"{pdf_path} has {page_count} pages; expected exactly 1 page.")
    return page_count


def enforce_one_page_pdf(**context: Any) -> tuple[Path, int]:
    import scripts.job_creation.claude_payload as claude_payload
    import scripts.job_creation.cv_output as cv_output
    import scripts.job_creation.one_page as one_page

    cv_output.compile_pdf_and_count_pages = compile_pdf_and_count_pages
    cv_output.generate_cv = generate_cv
    claude_payload.call_anthropic = call_anthropic
    one_page.call_claude_for_valid_payload = call_claude_for_valid_payload
    one_page.compile_pdf_and_count_pages = compile_pdf_and_count_pages
    one_page.generate_cv = generate_cv
    return one_page.enforce_one_page_pdf(**context)


if __name__ == "__main__":
    raise SystemExit(main())
