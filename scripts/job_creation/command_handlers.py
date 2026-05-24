from __future__ import annotations

import argparse, subprocess, sys
from pathlib import Path
from pydantic import ValidationError

from scripts.generate_cv import CvGenerationError
from .errors import IntakeError, InteractiveQuit
from .paths import ROOT
from .resolvers import resolve_job_description, resolve_revision_feedback
from .cv_requirements import resolve_cv_requirements
from .results import print_generation_result
from .workflows import create_job_from_inputs, refine_job_with_feedback

def create_new_job(args: argparse.Namespace, master_data_path: Path) -> int:
    try:
        job_description, default_job_id = resolve_job_description(args)
        cv_requirements = resolve_cv_requirements(args)
        job_folder, tex_path, pdf_page_count = create_job_from_inputs(
            args,
            master_data_path,
            job_description,
            cv_requirements,
            default_job_id,
        )
        if args.provider == "prompt-only":
            return 0
    except (
        CvGenerationError,
        IntakeError,
        InteractiveQuit,
        ValidationError,
        subprocess.CalledProcessError,
    ) as exc:
        if isinstance(exc, InteractiveQuit):
            print("Interactive session exited.")
            return 0
        print(f"Job intake failed: {exc}", file=sys.stderr)
        return 1

    print_generation_result(
        job_folder,
        tex_path,
        pdf_page_count,
        refined=False,
        compile_pdf=args.compile_pdf,
    )
    return 0


def refine_existing_job(args: argparse.Namespace, master_data_path: Path) -> int:
    job_folder = args.refine_job
    if not job_folder.is_absolute():
        job_folder = ROOT / job_folder

    try:
        revision_feedback = resolve_revision_feedback(args)
        tex_path, pdf_page_count = refine_job_with_feedback(
            args,
            master_data_path,
            job_folder,
            revision_feedback,
        )
        if args.provider == "prompt-only":
            return 0
    except (
        CvGenerationError,
        IntakeError,
        InteractiveQuit,
        ValidationError,
        subprocess.CalledProcessError,
    ) as exc:
        if isinstance(exc, InteractiveQuit):
            print("Interactive session exited.")
            return 0
        print(f"Job refinement failed: {exc}", file=sys.stderr)
        return 1

    print_generation_result(
        job_folder,
        tex_path,
        pdf_page_count,
        refined=True,
        compile_pdf=args.compile_pdf,
    )
    return 0


