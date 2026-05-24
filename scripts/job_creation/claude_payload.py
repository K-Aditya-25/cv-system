from __future__ import annotations

import json
from typing import Any

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from .errors import IntakeError
from .llm import call_anthropic, parse_llm_json
from .prompting import yaml_text
from .skill_repair import validate_repaired_intake_payload

def build_validation_retry_prompt(
    validation_error: str,
    allowed_skills: dict[str, list[str]],
    previous_payload: dict[str, Any],
) -> str:
    return (
        "Your previous JSON failed validation.\n\n"
        "Validation error:\n"
        f"{validation_error.strip()}\n\n"
        "Allowed skills by category:\n"
        f"{yaml_text(allowed_skills).strip()}\n\n"
        "Rules:\n"
        "- Use only skills listed above.\n"
        "- Preserve all valid selections.\n"
        "- If a skill exists under a different category, place it under that exact category.\n"
        "- If a skill does not exist anywhere, remove it or replace it with the closest "
        "role-relevant allowed skill.\n"
        "- Keep spelling and capitalization exactly as listed.\n"
        "- Return the complete JSON object again with job_config, selection, "
        "job_summary_text, and selection_rationale.\n"
        "- Return JSON only.\n\n"
        "Previous JSON:\n"
        f"{json.dumps(previous_payload, indent=2, ensure_ascii=False)}"
    )


def call_claude_for_valid_payload(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    database: CareerDatabase,
    allow_longer_cv: bool,
    max_validation_retries: int = 1,
) -> tuple[dict[str, Any], JobConfig, Selection, list[str]]:
    raw_response = call_anthropic(system_prompt, user_prompt, model)
    payload = parse_llm_json(raw_response)
    validation_error: str | None = None
    repairs: list[str] = []

    for attempt in range(max_validation_retries + 1):
        try:
            job_config, selection, repairs = validate_repaired_intake_payload(
                payload,
                database,
                allow_longer_cv=allow_longer_cv,
            )
            return payload, job_config, selection, repairs
        except IntakeError as exc:
            validation_error = str(exc)
            if attempt == max_validation_retries:
                raise

        retry_prompt = build_validation_retry_prompt(
            validation_error,
            database.skills,
            payload,
        )
        raw_response = call_anthropic(system_prompt, retry_prompt, model)
        payload = parse_llm_json(raw_response)

    raise IntakeError(validation_error or "LLM response failed validation")

