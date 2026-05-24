from __future__ import annotations

from datetime import datetime
import re

from schemas.career_schema import JobConfig
from .constants import LONGER_CV_PATTERNS

def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value.strip().lower()).strip("_")
    slug = re.sub(r"_+", "_", slug)
    return slug or "new_job"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        raise IntakeError(f"Job description file not found: {path}") from None

def short_text_slug(text: str) -> str:
    words = re.findall(r"[A-Za-z0-9]+", text)
    if words:
        return slugify("_".join(words[:8]))[:80]
    return "pasted_job"


def timestamped_job_id() -> str:
    return f"job_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def job_config_folder_id(job_config: JobConfig) -> str:
    return slugify(f"{job_config.company}_{job_config.role}")

def explicitly_requests_longer_cv(*texts: str) -> bool:
    combined = " ".join(text.lower() for text in texts if text)
    return any(pattern in combined for pattern in LONGER_CV_PATTERNS)


def normalize_provider(provider: str) -> str:
    if provider == "anthropic":
        return "claude"
    return provider


def is_claude_provider(provider: str) -> bool:
    return normalize_provider(provider) == "claude"

