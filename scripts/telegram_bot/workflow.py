from __future__ import annotations

import argparse
import os
from pathlib import Path

from scripts.job_creation.constants import DEFAULT_ANTHROPIC_MODEL
from scripts.job_creation.cv_output import pdf_path_for_tex
from scripts.job_creation.model_catalog import default_model_route, model_route_for_key
from scripts.job_creation.model_logging import log_event
from scripts.job_creation.paths import ROOT
from scripts.job_creation.text_utils import short_text_slug
from scripts.job_creation.workflows import create_job_from_inputs, refine_job_with_feedback
from scripts.generate_cv import load_yaml


def workflow_args(model_key: str = "", provider: str = "", model: str = "") -> argparse.Namespace:
    if model_key:
        route = model_route_for_key(model_key) or default_model_route()
        provider, model = route.provider, route.model
        model_key = route.key
    provider = provider or os.environ.get("CV_LLM_PROVIDER", "claude")
    model = model or os.environ.get("CV_LLM_MODEL", DEFAULT_ANTHROPIC_MODEL)
    return argparse.Namespace(
        jobs_root=ROOT / "jobs",
        provider=provider,
        model=model,
        model_key=model_key,
        compile_pdf=True,
        job_id=None,
    )


def job_model_args(folder: Path) -> argparse.Namespace:
    metadata_path = folder / "llm_model.yaml"
    if metadata_path.exists():
        data = load_yaml(metadata_path)
        if isinstance(data, dict):
            return workflow_args(
                str(data.get("model_key") or ""),
                str(data.get("provider") or ""),
                str(data.get("model") or ""),
            )
    return workflow_args()


def job_model_key(folder: Path) -> str:
    metadata_path = folder / "llm_model.yaml"
    if not metadata_path.exists():
        return ""
    data = load_yaml(metadata_path)
    return str(data.get("model_key") or "") if isinstance(data, dict) else ""


class CvWorkflow:
    def __init__(self, master_data_path: Path):
        self.master_data_path = master_data_path

    def create(self, description: str, instructions: str, model_key: str = "") -> tuple[Path, Path]:
        args = workflow_args(model_key)
        log_event(
            "model.workflow", operation="create", phase="start", model_key=args.model_key,
            provider=args.provider, model=args.model, description_chars=len(description),
            instructions_chars=len(instructions),
        )
        folder, tex_path, _ = create_job_from_inputs(
            args, self.master_data_path, description, instructions, short_text_slug(description),
        )
        pdf_path = pdf_path_for_tex(tex_path)
        log_event(
            "model.workflow", operation="create", phase="complete", model_key=args.model_key,
            provider=args.provider, model=args.model, job_folder=folder,
            tex_path=tex_path, pdf_path=pdf_path,
        )
        return folder, pdf_path

    def refine(self, folder: Path, feedback: str, model_key: str = "") -> Path:
        args = workflow_args(model_key) if model_key else job_model_args(folder)
        log_event(
            "model.workflow", operation="refine", phase="start", model_key=args.model_key,
            provider=args.provider, model=args.model, job_folder=folder,
            feedback_chars=len(feedback),
        )
        tex_path, _ = refine_job_with_feedback(
            args, self.master_data_path, folder, feedback,
        )
        pdf_path = pdf_path_for_tex(tex_path)
        log_event(
            "model.workflow", operation="refine", phase="complete", model_key=args.model_key,
            provider=args.provider, model=args.model, tex_path=tex_path, pdf_path=pdf_path,
        )
        return pdf_path
