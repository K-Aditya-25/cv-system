from __future__ import annotations

from pathlib import Path

from .errors import IntakeError
from .text_utils import slugify

def unique_job_folder(jobs_root: Path, requested_job_id: str) -> Path:
    base_job_id = slugify(requested_job_id)
    candidate = jobs_root / base_job_id
    if not candidate.exists():
        return candidate
    for index in range(2, 1000):
        candidate = jobs_root / f"{base_job_id}_{index}"
        if not candidate.exists():
            return candidate
    raise IntakeError(f"Could not find an available job folder name for: {base_job_id}")

