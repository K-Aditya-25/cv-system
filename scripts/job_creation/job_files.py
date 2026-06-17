from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from schemas.career_schema import JobConfig, Selection
from .llm_metadata import write_llm_metadata
from .prompting import write_yaml


def _write_summary_and_rationale(job_folder: Path, payload: dict[str, Any]) -> None:
    summary = str(payload.get("job_summary_text") or "").strip()
    if summary:
        (job_folder / "job_summary.txt").write_text(summary + "\n", encoding="utf-8")
    rationale = payload.get("selection_rationale") or []
    if rationale:
        rationale_lines = ["# Selection Rationale", ""]
        rationale_lines.extend(f"- {item}" for item in rationale)
        (job_folder / "selection_rationale.md").write_text(
            "\n".join(rationale_lines) + "\n", encoding="utf-8"
        )


def _prompt_text(system_prompt: str, user_prompt: str) -> str:
    return "# System Prompt\n\n" + system_prompt.strip() + "\n\n# User Prompt\n\n" + user_prompt.strip() + "\n"


def write_job_files(
    job_folder: Path,
    job_description: str,
    cv_requirements: str,
    system_prompt: str,
    user_prompt: str,
    payload: dict[str, Any],
    job_config: JobConfig,
    selection: Selection,
    *,
    llm_provider: str = "",
    llm_model: str = "",
    llm_model_key: str = "",
) -> None:
    job_folder.mkdir(parents=True, exist_ok=False)
    (job_folder / "job_description.md").write_text(job_description + "\n", encoding="utf-8")
    (job_folder / "cv_requirements.md").write_text(cv_requirements + "\n", encoding="utf-8")
    (job_folder / "llm_prompt.md").write_text(_prompt_text(system_prompt, user_prompt), encoding="utf-8")
    write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
    write_yaml(job_folder / "selection.yaml", selection.model_dump(mode="json"))
    write_llm_metadata(job_folder, llm_provider, llm_model, llm_model_key)
    _write_summary_and_rationale(job_folder, payload)


def write_prompt_file(path: Path, system_prompt: str, user_prompt: str) -> None:
    path.write_text(_prompt_text(system_prompt, user_prompt), encoding="utf-8")


def append_revision_feedback(job_folder: Path, feedback: str) -> None:
    feedback_path = job_folder / "revision_feedback.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with feedback_path.open("a", encoding="utf-8") as file:
        file.write(f"## {timestamp}\n\n{feedback.strip()}\n\n")


def append_one_page_enforcement_prompt(job_folder: Path, attempt: int, page_count: int, system_prompt: str, user_prompt: str) -> None:
    prompt_path = job_folder / "one_page_enforcement.md"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with prompt_path.open("a", encoding="utf-8") as file:
        file.write(
            f"## {timestamp} - Attempt {attempt}\n\n"
            f"Detected PDF pages: {page_count}\n\n"
            + _prompt_text(system_prompt, user_prompt)
            + "\n"
        )


def write_revised_job_files(
    job_folder: Path,
    revision_feedback: str,
    system_prompt: str,
    user_prompt: str,
    payload: dict[str, Any],
    job_config: JobConfig,
    selection: Selection,
    *,
    llm_provider: str = "",
    llm_model: str = "",
    llm_model_key: str = "",
) -> None:
    append_revision_feedback(job_folder, revision_feedback)
    write_prompt_file(job_folder / "llm_refine_prompt.md", system_prompt, user_prompt)
    write_yaml(job_folder / "job_config.yaml", job_config.model_dump(mode="json"))
    write_yaml(job_folder / "selection.yaml", selection.model_dump(mode="json"))
    write_llm_metadata(job_folder, llm_provider, llm_model, llm_model_key)
    _write_summary_and_rationale(job_folder, payload)
