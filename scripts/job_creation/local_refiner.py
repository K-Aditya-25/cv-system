from __future__ import annotations

import argparse
from typing import Any

from .candidate_inventory import build_candidate_inventory
from .cv_output import generate_cv
from .errors import IntakeError
from .job_files import write_revised_job_files
from .one_page import enforce_one_page_pdf
from .refinement_routes import LocalAction
from .validation_core import warn_selected_projects_without_portfolio_links


def refine_job_with_local_edit(args: argparse.Namespace, context: Any, feedback: str,
                               action: LocalAction) -> tuple[Any, int | None]:
    change = _apply_action(context, action)
    context.job_config = type(context.job_config).model_validate(
        context.job_config.model_dump(mode="json")
    )
    context.selection = type(context.selection).model_validate(
        context.selection.model_dump(mode="json")
    )
    payload = {
        "job_summary_text": _existing_summary(context.job_folder),
        "selection_rationale": [f"Applied deterministic local edit: {change}"],
    }
    write_revised_job_files(
        context.job_folder, feedback, "Deterministic local edit; no LLM request was sent.",
        feedback.strip(), payload, context.job_config, context.selection,
    )
    warn_selected_projects_without_portfolio_links(context.database, context.selection)
    tex_path = generate_cv(context.job_folder, context.database, context.job_config, context.selection)
    if not args.compile_pdf:
        return tex_path, None
    return enforce_one_page_pdf(
        job_folder=context.job_folder, database=context.database,
        job_description=context.job_description, cv_requirements=context.cv_requirements,
        candidate_inventory=build_candidate_inventory(context.database),
        system_prompt="Deterministic local edit; no LLM request was sent.", model=args.model,
        job_config=context.job_config, selection=context.selection, tex_path=tex_path,
        preserve_revision_feedback=feedback,
    )


def _apply_action(context: Any, action: LocalAction) -> str:
    if action.type == "set_job_config_field":
        if not action.field:
            raise IntakeError("Local edit is missing a job_config field.")
        setattr(context.job_config, action.field, action.value)
        return f"set job_config.{action.field}"
    if action.type == "remove_section":
        return _remove_section(context, action.section)
    if action.type == "remove_selected_item":
        return _remove_selected_item(context.selection, action.item_kind, action.item_id)
    if action.type == "remove_skill_category":
        return _remove_skill_category(context.selection, action.field)
    raise IntakeError(f"Unsupported local edit action: {action.type}")


def _remove_section(context: Any, section: str | None) -> str:
    if not section:
        raise IntakeError("Local edit is missing a section.")
    if context.job_config.sections_order:
        context.job_config.sections_order = [
            value for value in context.job_config.sections_order if value != section
        ]
    context.selection.custom_sections.pop(section, None)
    return f"remove section {section}"


def _remove_selected_item(selection: Any, kind: str | None, item_id: str | None) -> str:
    if not kind or not item_id:
        raise IntakeError("Local edit is missing a selected item target.")
    values = getattr(selection, kind)
    if kind in ("experience", "projects"):
        setattr(selection, kind, [item for item in values if item.id != item_id])
    else:
        setattr(selection, kind, [item for item in values if item != item_id])
    return f"remove selected {kind}.{item_id}"


def _remove_skill_category(selection: Any, category: str | None) -> str:
    if not category:
        raise IntakeError("Local edit is missing a skills category.")
    selection.skills.pop(category, None)
    return f"remove skills.{category}"


def _existing_summary(job_folder: Any) -> str:
    summary_path = job_folder / "job_summary.txt"
    if summary_path.exists():
        return summary_path.read_text(encoding="utf-8").strip()
    return "Existing CV refined by deterministic local edit."
