from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.job_creation.constants import DEFAULT_ANTHROPIC_MODEL
from scripts.job_creation.cv_output import pdf_path_for_tex
from scripts.job_creation.paths import ROOT
from scripts.job_creation.text_utils import short_text_slug
from scripts.job_creation.workflows import create_job_from_inputs, refine_job_with_feedback


def workflow_args() -> argparse.Namespace:
    return argparse.Namespace(
        jobs_root=ROOT / "jobs", provider="claude", model=os.environ.get(
            "CV_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL,
        ), compile_pdf=True, job_id=None,
    )


class CvWorkflow:
    def __init__(self, master_data_path: Path):
        self.master_data_path = master_data_path

    def create(self, description: str, instructions: str) -> tuple[Path, Path]:
        folder, tex_path, _ = create_job_from_inputs(
            workflow_args(), self.master_data_path, description, instructions,
            short_text_slug(description),
        )
        return folder, pdf_path_for_tex(tex_path)

    def refine(self, folder: Path, feedback: str) -> Path:
        tex_path, _ = refine_job_with_feedback(
            workflow_args(), self.master_data_path, folder, feedback,
        )
        return pdf_path_for_tex(tex_path)
