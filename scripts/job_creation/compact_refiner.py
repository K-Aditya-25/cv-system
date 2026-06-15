from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from .claude_payload import call_claude_for_valid_payload
from .candidate_inventory import build_candidate_inventory
from .cv_output import generate_cv
from .job_files import append_revision_feedback, write_prompt_file, write_revised_job_files
from .one_page import enforce_one_page_pdf
from .prompting import render_prompt_template, yaml_text
from .text_utils import explicitly_requests_longer_cv, is_claude_provider
from .validation_core import report_skill_repairs, warn_selected_projects_without_portfolio_links
from .errors import IntakeError


def refine_job_with_compact_prompt(
    args: argparse.Namespace,
    context: Any,
    revision_feedback: str,
) -> tuple[Path, int | None]:
    system_prompt = render_prompt_template("job_intake_system.md")
    user_prompt = _compact_prompt(context, revision_feedback)
    if args.provider == "prompt-only":
        append_revision_feedback(context.job_folder, revision_feedback)
        prompt_path = context.job_folder / "llm_refine_prompt.md"
        write_prompt_file(prompt_path, system_prompt, user_prompt)
        print(f"Wrote compact refinement prompt to {prompt_path}")
        return prompt_path, None
    if not is_claude_provider(args.provider):
        raise IntakeError(f"Unsupported provider: {args.provider}")
    payload, job_config, selection, repairs = call_claude_for_valid_payload(
        system_prompt=system_prompt, user_prompt=user_prompt, model=args.model,
        database=context.database,
        allow_longer_cv=explicitly_requests_longer_cv(
            context.cv_requirements, revision_feedback,
        ),
    )
    report_skill_repairs(repairs)
    warn_selected_projects_without_portfolio_links(context.database, selection)
    write_revised_job_files(
        context.job_folder, revision_feedback, system_prompt, user_prompt,
        payload, job_config, selection,
    )
    tex_path = generate_cv(context.job_folder, context.database, job_config, selection)
    if not args.compile_pdf:
        return tex_path, None
    return enforce_one_page_pdf(
        job_folder=context.job_folder, database=context.database,
        job_description=context.job_description, cv_requirements=context.cv_requirements,
        candidate_inventory=build_candidate_inventory(context.database),
        system_prompt=system_prompt, model=args.model, job_config=job_config,
        selection=selection, tex_path=tex_path,
    )


def _compact_prompt(context, revision_feedback: str) -> str:
    return render_prompt_template(
        "job_refine_compact_user.md.j2",
        cv_requirements=context.cv_requirements,
        revision_feedback=revision_feedback,
        current_job_config=yaml_text(context.job_config.model_dump(mode="json")),
        current_selection=yaml_text(context.selection.model_dump(mode="json")),
        current_job_tex=context.current_tex,
    )
