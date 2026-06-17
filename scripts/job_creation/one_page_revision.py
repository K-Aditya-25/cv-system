from __future__ import annotations

from pathlib import Path
from typing import Any

from schemas.career_schema import JobConfig, Selection
from .claude_payload import call_model_for_valid_payload
from .job_files import append_one_page_enforcement_prompt
from .page_fit import build_one_page_enforcement_feedback
from .prompting import render_prompt_template, yaml_text
from .validation_core import report_skill_repairs

def _request_one_page_revision(context: dict[str, Any]) -> tuple[dict[str, Any], JobConfig, Selection, str]:
    revision_feedback = build_one_page_enforcement_feedback(
        context["page_count"], context["llm_call"], context["compact_margin"],
        context["removed_additional_information"], context["validation_error"],
        context.get("preserve_revision_feedback"),
    )
    user_prompt = render_prompt_template(
        "job_refine_user.md.j2", job_description=context["job_description"],
        cv_requirements=context["cv_requirements"], revision_feedback=revision_feedback,
        current_job_config=yaml_text(context["job_config"].model_dump(mode="json")),
        current_selection=yaml_text(context["selection"].model_dump(mode="json")),
        candidate_inventory=context["candidate_inventory"],
    )
    append_one_page_enforcement_prompt(context["job_folder"], context["llm_call"], context["page_count"], context["system_prompt"], user_prompt)
    payload, job_config, selection, repairs = call_model_for_valid_payload(
        system_prompt=context["system_prompt"], user_prompt=user_prompt,
        provider=context.get("provider", "claude"), model=context["model"],
        database=context["database"], allow_longer_cv=False, max_validation_retries=0,
    )
    report_skill_repairs(repairs)
    return payload, job_config, selection, revision_feedback, user_prompt
