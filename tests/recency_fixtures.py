from schemas.career_schema import CareerDatabase, JobConfig, Selection


def bullet(bullet_id: str) -> dict[str, object]:
    return {"id": bullet_id, "text": f"Bullet {bullet_id}", "tags": [], "strength": 3}


def database() -> CareerDatabase:
    return CareerDatabase.model_validate(
        {
            "profile": {"name": "Alex Example", "email": "alex@example.com"},
            "experience": [
                {
                    "id": "older_role", "company": "OlderCo", "title": "Engineer",
                    "start_date": "Jan 2024", "end_date": "Dec 2024",
                    "bullets": [bullet("older_bullet")],
                },
                {
                    "id": "current_role", "company": "CurrentCo", "title": "Engineer",
                    "start_date": "Jan 2025", "end_date": "Present",
                    "bullets": [bullet("current_bullet")],
                },
                {
                    "id": "recent_finished_role", "company": "RecentCo", "title": "Engineer",
                    "start_date": "Oct 2025", "end_date": "Mar 2026",
                    "bullets": [bullet("recent_bullet")],
                },
            ],
            "projects": [
                {"id": "older_project", "name": "Older Project", "date": "2024",
                 "bullets": [bullet("older_project_bullet")]},
                {"id": "current_project", "name": "Current Project", "date": "Present",
                 "bullets": [bullet("current_project_bullet")]},
                {"id": "recent_project", "name": "Recent Project", "date": "Feb 2026",
                 "bullets": [bullet("recent_project_bullet")]},
            ],
        }
    )


def selection() -> Selection:
    return Selection.model_validate(
        {
            "experience": [
                {"id": "older_role", "bullets": ["older_bullet"]},
                {"id": "recent_finished_role", "bullets": ["recent_bullet"]},
                {"id": "current_role", "bullets": ["current_bullet"]},
            ],
            "projects": [
                {"id": "older_project", "bullets": ["older_project_bullet"]},
                {"id": "recent_project", "bullets": ["recent_project_bullet"]},
                {"id": "current_project", "bullets": ["current_project_bullet"]},
            ],
        }
    )


def job_config() -> JobConfig:
    return JobConfig.model_validate(
        {"company": "Target", "role": "Engineer", "output_name": "target_engineer"}
    )
