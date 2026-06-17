from __future__ import annotations

from pathlib import Path

from .prompting import write_yaml


def write_llm_metadata(
    job_folder: Path,
    provider: str,
    model: str,
    model_key: str = "",
) -> None:
    if not provider and not model and not model_key:
        return
    write_yaml(
        job_folder / "llm_model.yaml",
        {"provider": provider, "model": model, "model_key": model_key},
    )
