from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from schemas.career_schema import JobConfig
from scripts.generate_cv import load_yaml, safe_latex_name


@dataclass(frozen=True)
class JobChoice:
    folder: Path
    pdf: Path
    label: str


def available_jobs(jobs_root: Path) -> list[JobChoice]:
    jobs: list[JobChoice] = []
    for config_path in jobs_root.glob("*/job_config.yaml"):
        try:
            config = JobConfig.model_validate(load_yaml(config_path))
        except Exception:
            continue
        pdf = config_path.parent / Path(safe_latex_name(config.output_name)).with_suffix(".pdf")
        if pdf.exists():
            jobs.append(JobChoice(config_path.parent, pdf, f"{config.company} - {config.role}"))
    return sorted(jobs, key=lambda job: job.folder.stat().st_mtime, reverse=True)


def numbered_jobs(jobs: list[JobChoice]) -> str:
    lines = ["Choose a CV to refine by replying with its number:"]
    lines.extend(f"{index}. {job.label}" for index, job in enumerate(jobs, start=1))
    return "\n".join(lines)
