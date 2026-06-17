from __future__ import annotations

import argparse
from pathlib import Path

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.generate_cv import load_yaml
from .claude_payload import call_model_for_valid_payload
from .constants import DEFAULT_CV_REQUIREMENTS
from .cv_output import generate_cv
from .errors import IntakeError
from .job_files import append_revision_feedback, write_prompt_file, write_revised_job_files
from .one_page import enforce_one_page_pdf
from .paths import ROOT
from .candidate_inventory import build_candidate_inventory
from .prompting import render_prompt_template, yaml_text
from .resolvers import read_text
from .text_utils import explicitly_requests_longer_cv, is_llm_provider
from .validation_core import report_skill_repairs, warn_selected_projects_without_portfolio_links

def refine_job_with_feedback(
    args: argparse.Namespace,
    master_data_path: Path,
    job_folder: Path,
    revision_feedback: str,
) -> tuple[Path, int | None]:
    if not job_folder.is_absolute():
        job_folder = ROOT / job_folder
    if not job_folder.exists():
        raise IntakeError(f"Job folder does not exist: {job_folder}")

    database = CareerDatabase.model_validate(load_yaml(master_data_path))
    current_job_config = JobConfig.model_validate(load_yaml(job_folder / "job_config.yaml"))
    current_selection = Selection.model_validate(load_yaml(job_folder / "selection.yaml"))
    job_description = read_text(job_folder / "job_description.md")
    cv_requirements_path = job_folder / "cv_requirements.md"
    cv_requirements = (
        read_text(cv_requirements_path)
        if cv_requirements_path.exists()
        else DEFAULT_CV_REQUIREMENTS
    )
    candidate_inventory = build_candidate_inventory(database)
    system_prompt = render_prompt_template("job_intake_system.md")
    user_prompt = render_prompt_template(
        "job_refine_user.md.j2",
        job_description=job_description,
        cv_requirements=cv_requirements,
        revision_feedback=revision_feedback,
        current_job_config=yaml_text(current_job_config.model_dump(mode="json")),
        current_selection=yaml_text(current_selection.model_dump(mode="json")),
        candidate_inventory=candidate_inventory,
    )

    if args.provider == "prompt-only":
        append_revision_feedback(job_folder, revision_feedback)
        write_prompt_file(job_folder / "llm_refine_prompt.md", system_prompt, user_prompt)
        print(f"Wrote refinement prompt to {job_folder / 'llm_refine_prompt.md'}")
        print("Run again with --provider claude or --provider tensorix to revise YAML and regenerate the CV.")
        return job_folder / "llm_refine_prompt.md", None

    if not is_llm_provider(args.provider):
        raise IntakeError(f"Unsupported provider: {args.provider}")

    payload, job_config, selection, repairs = call_model_for_valid_payload(
        system_prompt=system_prompt, user_prompt=user_prompt,
        provider=args.provider, model=args.model,
        database=database,
        allow_longer_cv=explicitly_requests_longer_cv(cv_requirements, revision_feedback),
    )
    report_skill_repairs(repairs)
    warn_selected_projects_without_portfolio_links(database, selection)
    write_revised_job_files(
        job_folder, revision_feedback, system_prompt, user_prompt, payload, job_config, selection,
        llm_provider=args.provider,
        llm_model=args.model,
        llm_model_key=getattr(args, "model_key", ""),
    )
    tex_path = generate_cv(job_folder, database, job_config, selection)
    pdf_page_count: int | None = None
    if args.compile_pdf:
        tex_path, pdf_page_count = enforce_one_page_pdf(
            job_folder=job_folder,
            database=database,
            job_description=job_description,
            cv_requirements=cv_requirements,
            candidate_inventory=candidate_inventory,
            system_prompt=system_prompt,
            provider=args.provider,
            model=args.model,
            model_key=getattr(args, "model_key", ""),
            job_config=job_config,
            selection=selection,
            tex_path=tex_path,
            preserve_revision_feedback=revision_feedback,
        )
    return tex_path, pdf_page_count
