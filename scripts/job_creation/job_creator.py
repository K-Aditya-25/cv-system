from __future__ import annotations

import argparse
from pathlib import Path

from schemas.career_schema import CareerDatabase
from scripts.generate_cv import load_yaml
from .claude_payload import call_model_for_valid_payload
from .cv_output import generate_cv
from .errors import IntakeError
from .folders import unique_job_folder
from .job_files import write_job_files, write_prompt_file
from .one_page import enforce_one_page_pdf
from .paths import ROOT
from .candidate_inventory import build_candidate_inventory
from .prompting import render_prompt_template
from .text_utils import explicitly_requests_longer_cv, is_llm_provider, job_config_folder_id, slugify, timestamped_job_id
from .validation_core import report_skill_repairs, warn_selected_projects_without_portfolio_links

def create_job_from_inputs(
    args: argparse.Namespace,
    master_data_path: Path,
    job_description: str,
    cv_requirements: str,
    default_job_id: str,
) -> tuple[Path, Path, int | None]:
    jobs_root = args.jobs_root if args.jobs_root.is_absolute() else ROOT / args.jobs_root
    database = CareerDatabase.model_validate(load_yaml(master_data_path))
    candidate_inventory = build_candidate_inventory(database)
    system_prompt = render_prompt_template("job_intake_system.md")
    user_prompt = render_prompt_template(
        "job_intake_user.md.j2",
        job_description=job_description,
        cv_requirements=cv_requirements,
        candidate_inventory=candidate_inventory,
    )

    if args.provider == "prompt-only":
        job_id = slugify(args.job_id or default_job_id or timestamped_job_id())
        job_folder = unique_job_folder(jobs_root, job_id)
        job_folder.mkdir(parents=True, exist_ok=False)
        (job_folder / "job_description.md").write_text(
            job_description + "\n", encoding="utf-8"
        )
        (job_folder / "cv_requirements.md").write_text(cv_requirements + "\n", encoding="utf-8")
        write_prompt_file(job_folder / "llm_prompt.md", system_prompt, user_prompt)
        print(f"Wrote prompt package to {job_folder}")
        print("Run again with --provider claude or --provider tensorix to generate YAML and CV automatically.")
        return job_folder, job_folder / "llm_prompt.md", None

    if not is_llm_provider(args.provider):
        raise IntakeError(f"Unsupported provider: {args.provider}")

    payload, job_config, selection, repairs = call_model_for_valid_payload(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        provider=args.provider,
        model=args.model,
        database=database,
        allow_longer_cv=explicitly_requests_longer_cv(cv_requirements),
    )
    report_skill_repairs(repairs)
    warn_selected_projects_without_portfolio_links(database, selection)
    job_id = slugify(args.job_id) if args.job_id else job_config_folder_id(job_config)
    job_folder = unique_job_folder(jobs_root, job_id)
    write_job_files(
        job_folder,
        job_description,
        cv_requirements,
        system_prompt,
        user_prompt,
        payload,
        job_config,
        selection,
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
        )
    return job_folder, tex_path, pdf_page_count
