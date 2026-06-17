from __future__ import annotations

from pathlib import Path
from typing import Any

from .constants import MAX_AUTOMATIC_ONE_PAGE_LLM_CALLS, MAX_COMPILE_PDF_LLM_CALLS, ONE_PAGE_LIMIT
from .cv_output import compile_pdf_and_count_pages, generate_cv, pdf_path_for_tex
from .errors import IntakeError
from .job_files import write_revised_job_files
from .one_page_revision import _request_one_page_revision
from .page_fit import compact_page_margin, remove_additional_information_section, should_retry_llm_revision_error
from .prompting import write_yaml
from .validation_core import warn_selected_projects_without_portfolio_links


def _try_compact_margin(job_folder: Path, database: CareerDatabase, job_config: JobConfig, selection: Selection) -> tuple[Path, int, str]:
    compact_margin = compact_page_margin(job_config)
    print(f"Compiled PDF has {{_try_compact_margin.page_count}} pages; retrying with compact {compact_margin} page margins before using an LLM revision.")
    job_config.page_margin = compact_margin
    write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
    tex_path = generate_cv(job_folder, database, job_config, selection)
    page_count = compile_pdf_and_count_pages(tex_path)
    return tex_path, page_count, compact_margin


def _try_remove_additional_information(job_folder: Path, database: CareerDatabase, job_config: JobConfig, selection: Selection) -> tuple[Path | None, int | None, bool]:
    removed_additional_information = remove_additional_information_section(job_config, selection)
    if removed_additional_information:
        write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
        write_yaml(job_folder / "selection.yaml", selection.model_dump(mode="json"))
        tex_path = generate_cv(job_folder, database, job_config, selection)
        return tex_path, compile_pdf_and_count_pages(tex_path), True
    print("No additional_information section was present to remove.")
    return None, None, False


def _compile_revision(job_folder: Path, database: CareerDatabase, job_config: JobConfig, selection: Selection, tex_path: Path) -> tuple[Path, int]:
    tex_path = generate_cv(job_folder, database, job_config, selection)
    return tex_path, compile_pdf_and_count_pages(tex_path)


def _warn_enforcement_exhausted(tex_path: Path, page_count: int) -> None:
    print(
        "One-page PDF enforcement failed after compact margin fallback, "
        "additional_information removal, and "
        f"{MAX_COMPILE_PDF_LLM_CALLS} total LLM calls: "
        f"{pdf_path_for_tex(tex_path)} has {page_count} pages. "
        "Delivering the best compiled PDF; send refinement feedback to cut content."
    )


def enforce_one_page_pdf(**context: Any) -> tuple[Path, int]:
    tex_path = context["tex_path"]
    page_count = compile_pdf_and_count_pages(tex_path)
    if page_count == ONE_PAGE_LIMIT:
        return tex_path, page_count
    _try_compact_margin.page_count = page_count
    tex_path, page_count, compact_margin = _try_compact_margin(context["job_folder"], context["database"], context["job_config"], context["selection"])
    if page_count == ONE_PAGE_LIMIT:
        return tex_path, page_count
    print(f"Compiled PDF still has {page_count} pages with compact margins; removing additional_information before using an LLM revision.")
    removed_tex_path, removed_page_count, removed = _try_remove_additional_information(context["job_folder"], context["database"], context["job_config"], context["selection"])
    if removed_tex_path is not None and removed_page_count is not None:
        tex_path, page_count = removed_tex_path, removed_page_count
        if page_count == ONE_PAGE_LIMIT:
            return tex_path, page_count
    validation_error = None
    for llm_call in range(1, MAX_AUTOMATIC_ONE_PAGE_LLM_CALLS + 1):
        print(f"Compiled PDF still has {page_count} pages after compact margins and additional_information removal; requesting one-page LLM revision {llm_call}/{MAX_AUTOMATIC_ONE_PAGE_LLM_CALLS}.")
        try:
            revision_context = dict(context, page_count=page_count, llm_call=llm_call, compact_margin=compact_margin, removed_additional_information=removed, validation_error=validation_error)
            payload, job_config, selection, revision_feedback, user_prompt = _request_one_page_revision(revision_context)
            job_config.page_margin = compact_margin
            remove_additional_information_section(job_config, selection)
            warn_selected_projects_without_portfolio_links(context["database"], selection)
        except IntakeError as exc:
            if not should_retry_llm_revision_error(exc):
                raise
            validation_error = str(exc)
            if llm_call == MAX_AUTOMATIC_ONE_PAGE_LLM_CALLS:
                raise IntakeError("One-page PDF enforcement exhausted the compile-PDF LLM call budget " f"of {MAX_COMPILE_PDF_LLM_CALLS} total calls; last revision was invalid: " f"{validation_error}") from exc
            print("One-page revision failed validation; using the next and final automatic LLM call for a corrected revision.")
            continue
        write_revised_job_files(
            context["job_folder"],
            revision_feedback,
            context["system_prompt"],
            user_prompt,
            payload,
            job_config,
            selection,
            llm_provider=context.get("provider", "claude"),
            llm_model=context["model"],
            llm_model_key=context.get("model_key", ""),
        )
        tex_path, page_count = _compile_revision(context["job_folder"], context["database"], job_config, selection, tex_path)
        if page_count == ONE_PAGE_LIMIT:
            return tex_path, page_count
    _warn_enforcement_exhausted(tex_path, page_count)
    return tex_path, page_count
