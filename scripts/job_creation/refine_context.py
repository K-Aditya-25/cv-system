from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.generate_cv import load_yaml, safe_latex_name
from .constants import DEFAULT_CV_REQUIREMENTS
from .errors import IntakeError
from .paths import ROOT
from .resolvers import read_text


@dataclass
class RefineContext:
    job_folder: Path
    database: CareerDatabase
    job_config: JobConfig
    selection: Selection
    job_description: str
    cv_requirements: str
    current_tex: str


def normalize_job_folder(job_folder: Path) -> Path:
    folder = job_folder if job_folder.is_absolute() else ROOT / job_folder
    if not folder.exists():
        raise IntakeError(f"Job folder does not exist: {folder}")
    return folder


def current_tex_path(job_folder: Path, job_config: JobConfig) -> Path:
    expected = job_folder / safe_latex_name(job_config.output_name)
    if expected.exists():
        return expected
    candidates = sorted(
        job_folder.glob("*.tex"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else expected


def load_refine_context(master_data_path: Path, job_folder: Path) -> RefineContext:
    folder = normalize_job_folder(job_folder)
    database = CareerDatabase.model_validate(load_yaml(master_data_path))
    job_config = JobConfig.model_validate(load_yaml(folder / "job_config.yaml"))
    selection = Selection.model_validate(load_yaml(folder / "selection.yaml"))
    requirements_path = folder / "cv_requirements.md"
    cv_requirements = (
        read_text(requirements_path)
        if requirements_path.exists()
        else DEFAULT_CV_REQUIREMENTS
    )
    tex_path = current_tex_path(folder, job_config)
    current_tex = read_text(tex_path) if tex_path.exists() else ""
    return RefineContext(
        job_folder=folder,
        database=database,
        job_config=job_config,
        selection=selection,
        job_description=read_text(folder / "job_description.md"),
        cv_requirements=cv_requirements,
        current_tex=current_tex,
    )
