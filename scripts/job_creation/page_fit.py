from __future__ import annotations

import re

from schemas.career_schema import JobConfig, Selection
from scripts.generate_cv import DEFAULT_PAGE_MARGIN
from .constants import ADDITIONAL_INFORMATION_SECTION
from .errors import IntakeError

def halve_margin(margin: str) -> str:
    match = re.fullmatch(r"\s*(\d+(?:\.\d+)?)([A-Za-z]+)\s*", margin)
    if not match:
        raise IntakeError(f"Cannot halve unsupported LaTeX margin value: {margin}")
    value = float(match.group(1)) / 2
    unit = match.group(2)
    return f"{value:g}{unit}"


def compact_page_margin(job_config: JobConfig) -> str:
    return halve_margin(job_config.page_margin or DEFAULT_PAGE_MARGIN)


def remove_additional_information_section(job_config: JobConfig, selection: Selection) -> bool:
    removed = False
    if job_config.sections_order and ADDITIONAL_INFORMATION_SECTION in job_config.sections_order:
        job_config.sections_order = [
            section
            for section in job_config.sections_order
            if section != ADDITIONAL_INFORMATION_SECTION
        ]
        removed = True

    if ADDITIONAL_INFORMATION_SECTION in selection.custom_sections:
        selection.custom_sections.pop(ADDITIONAL_INFORMATION_SECTION, None)
        removed = True

    return removed


def build_one_page_enforcement_feedback(
    page_count: int,
    attempt: int,
    compact_margin: str,
    removed_additional_information: bool,
    validation_error: str | None = None,
) -> str:
    additional_information_status = (
        "removed the additional_information section"
        if removed_additional_information
        else "confirmed there was no additional_information section left to remove"
    )
    feedback = (
        f"Automatic one-page PDF enforcement attempt {attempt}.\n\n"
        f"The compiled CV PDF still has {page_count} pages after the workflow reduced "
        f"the LaTeX page margin to {compact_margin} and {additional_information_status}. "
        "This workflow requires the final CV to fit on exactly one PDF page, so revise "
        "the complete job_config and complete selection to make the rendered CV fit on "
        "one page.\n\n"
        "Keep output_name unchanged. Set cv_length to \"one_page\". Reduce content by "
        "summarizing and selecting only the content that is absolutely necessary for "
        "this job. Remove the lowest-priority sections, items, bullets, skills, coursework, "
        "education bullets, and inline technology lists as needed. Prefer fewer stronger "
        "items over broad coverage. Do not rely on further margin reductions or the "
        "additional_information section. Return the full revised JSON object, not a patch."
    )
    if validation_error:
        feedback += (
            "\n\nThe previous automatic revision was rejected by validation:\n"
            f"{validation_error}\n\n"
            "Return a corrected one-page revision that satisfies every schema and selection rule."
        )
    return feedback


def should_retry_llm_revision_error(error: IntakeError) -> bool:
    message = str(error)
    non_retryable_prefixes = (
        "ANTHROPIC_API_KEY",
        "Anthropic API request failed",
        "Anthropic API response did not contain text",
    )
    return not message.startswith(non_retryable_prefixes)

