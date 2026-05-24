from __future__ import annotations

import subprocess, sys
from pathlib import Path
from pydantic import ValidationError

from scripts.generate_cv import CvGenerationError, load_yaml, safe_latex_name
from schemas.career_schema import JobConfig
from .constants import DEFAULT_CV_REQUIREMENTS
from .errors import IntakeError, InteractiveQuit
from .input_reader import read_multiline_input
from .paths import ROOT
from .results import print_generation_result
from .tex_watcher import TexCompileWatcher
from .text_utils import short_text_slug
from .workflows import create_job_from_inputs, refine_job_with_feedback

def current_tex_path_for_job(job_folder: Path) -> Path:
    current_job_config = JobConfig.model_validate(load_yaml(job_folder / "job_config.yaml"))
    return job_folder / safe_latex_name(current_job_config.output_name)


def run_interactive_claude_session(args: argparse.Namespace, master_data_path: Path) -> int:
    print("Starting Claude CV session. Press Ctrl-Q at any prompt to exit.")
    watcher = TexCompileWatcher()
    watcher.start()
    try:
        if args.refine_job:
            job_folder = args.refine_job
            if not job_folder.is_absolute():
                job_folder = ROOT / job_folder
            if not job_folder.exists():
                raise IntakeError(f"Job folder does not exist: {job_folder}")
            if args.compile_pdf:
                watcher.set_path(current_tex_path_for_job(job_folder))
        else:
            job_description = read_multiline_input("Job description")
            if not job_description:
                raise IntakeError("Job description cannot be empty")
            cv_requirements = read_multiline_input(
                "Custom CV prompt, requirements, or changes. Leave empty if you have none."
            )
            if not cv_requirements:
                cv_requirements = DEFAULT_CV_REQUIREMENTS
            watcher.pause()
            job_folder, tex_path, pdf_page_count = create_job_from_inputs(
                args,
                master_data_path,
                job_description,
                cv_requirements,
                short_text_slug(job_description),
            )
            watcher.set_path(tex_path if args.compile_pdf else None)
            watcher.resume()
            print_generation_result(
                job_folder,
                tex_path,
                pdf_page_count,
                refined=False,
                compile_pdf=args.compile_pdf,
            )

        while True:
            revision_feedback = read_multiline_input(
                "\nReview the generated CV, then enter refinement feedback"
            )
            if not revision_feedback:
                print("No feedback entered; waiting for changes or Ctrl-Q.")
                continue
            watcher.pause()
            tex_path, pdf_page_count = refine_job_with_feedback(
                args,
                master_data_path,
                job_folder,
                revision_feedback,
            )
            watcher.set_path(tex_path if args.compile_pdf else None)
            watcher.resume()
            print_generation_result(
                job_folder,
                tex_path,
                pdf_page_count,
                refined=True,
                compile_pdf=args.compile_pdf,
            )
    except InteractiveQuit:
        print("Interactive session exited.")
        return 0
    except (
        CvGenerationError,
        IntakeError,
        ValidationError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Interactive Claude session failed: {exc}", file=sys.stderr)
        return 1
    finally:
        watcher.stop()

    return 0
