from __future__ import annotations

import sys
from typing import Any
from pydantic import ValidationError

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from .constants import PROJECT_LINK_HOSTS
from .errors import IntakeError

def validate_intake_payload(
    payload: dict[str, Any],
    *,
    allow_longer_cv: bool,
) -> tuple[JobConfig, Selection]:
    try:
        job_config = JobConfig.model_validate(payload.get("job_config"))
        selection = Selection.model_validate(payload.get("selection"))
    except ValidationError as exc:
        raise IntakeError(f"Generated job config or selection failed schema validation:\n{exc}") from exc
    if not allow_longer_cv:
        job_config.cv_length = "one_page"
    return job_config, selection


def is_project_portfolio_link(link: Any) -> bool:
    text = f"{link.label} {link.url}".lower()
    return any(host in text for host in PROJECT_LINK_HOSTS)


def selected_projects_without_portfolio_links(
    database: CareerDatabase,
    selection: Selection,
) -> list[str]:
    projects_by_id = {project.id: project for project in database.projects}
    missing_links: list[str] = []
    for selected_project in selection.projects:
        project = projects_by_id.get(selected_project.id)
        if project is None:
            continue
        if not any(is_project_portfolio_link(link) for link in project.links):
            missing_links.append(selected_project.id)
    return missing_links


def warn_selected_projects_without_portfolio_links(
    database: CareerDatabase,
    selection: Selection,
) -> None:
    missing_links = selected_projects_without_portfolio_links(database, selection)
    if missing_links:
        print(
            "Warning: selected project(s) do not have a GitHub, Devpost, or Kaggle "
            "link in master data and will render without project links: "
            + ", ".join(missing_links),
            file=sys.stderr,
        )


def report_skill_repairs(repairs: list[str]) -> None:
    if repairs:
        print(
            "Canonicalized selected skill categorization: "
            + "; ".join(repairs),
            file=sys.stderr,
        )

