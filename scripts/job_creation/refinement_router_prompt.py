from __future__ import annotations

import json
from typing import Any

from .prompting import render_prompt_template, yaml_text


def planner_user_prompt(feedback: str, context: Any) -> str:
    return render_prompt_template(
        "refinement_router_user.md.j2",
        revision_feedback=feedback,
        company=context.job_config.company,
        role=context.job_config.role,
        current_job_config=yaml_text(context.job_config.model_dump(mode="json")),
        selection_summary=yaml_text(selection_summary(context.selection)),
        current_job_tex=context.current_tex[:20000],
    )


def selection_summary(selection: Any) -> dict[str, Any]:
    payload = selection.model_dump(mode="json")
    for key in ("experience", "projects"):
        payload[key] = [
            {"id": item["id"], "bullets": item.get("bullets", [])}
            for item in payload[key]
        ]
    return json.loads(json.dumps(payload))
