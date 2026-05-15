from __future__ import annotations

import unittest

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.generate_cv import build_render_context, parse_recency_date


def bullet(bullet_id: str) -> dict[str, object]:
    return {
        "id": bullet_id,
        "text": f"Bullet {bullet_id}",
        "tags": [],
        "strength": 3,
    }


class RecencyOrderingTests(unittest.TestCase):
    def test_generated_context_orders_experience_and_projects_by_recency(self) -> None:
        database = CareerDatabase.model_validate(
            {
                "profile": {"name": "Alex Example", "email": "alex@example.com"},
                "experience": [
                    {
                        "id": "older_role",
                        "company": "OlderCo",
                        "title": "Engineer",
                        "start_date": "Jan 2024",
                        "end_date": "Dec 2024",
                        "bullets": [bullet("older_bullet")],
                    },
                    {
                        "id": "current_role",
                        "company": "CurrentCo",
                        "title": "Engineer",
                        "start_date": "Jan 2025",
                        "end_date": "Present",
                        "bullets": [bullet("current_bullet")],
                    },
                    {
                        "id": "recent_finished_role",
                        "company": "RecentCo",
                        "title": "Engineer",
                        "start_date": "Oct 2025",
                        "end_date": "Mar 2026",
                        "bullets": [bullet("recent_bullet")],
                    },
                ],
                "projects": [
                    {
                        "id": "older_project",
                        "name": "Older Project",
                        "date": "2024",
                        "bullets": [bullet("older_project_bullet")],
                    },
                    {
                        "id": "current_project",
                        "name": "Current Project",
                        "date": "Present",
                        "bullets": [bullet("current_project_bullet")],
                    },
                    {
                        "id": "recent_project",
                        "name": "Recent Project",
                        "date": "Feb 2026",
                        "bullets": [bullet("recent_project_bullet")],
                    },
                ],
            }
        )
        selection = Selection.model_validate(
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
        job_config = JobConfig.model_validate(
            {
                "company": "Target",
                "role": "Engineer",
                "output_name": "target_engineer",
            }
        )

        context = build_render_context(database, job_config, selection)

        self.assertEqual(
            [item["id"] for item in context["experience"]],
            ["current_role", "recent_finished_role", "older_role"],
        )
        self.assertEqual(
            [item["id"] for item in context["projects"]],
            ["current_project", "recent_project", "older_project"],
        )

    def test_parse_recency_date_handles_common_cv_date_formats(self) -> None:
        self.assertEqual(parse_recency_date("Present"), (9999, 12, 31))
        self.assertEqual(parse_recency_date("Mar 2026"), (2026, 3, 31))
        self.assertEqual(parse_recency_date("2026-02"), (2026, 2, 28))
        self.assertEqual(parse_recency_date("Summer 2025"), (2025, 8, 31))
        self.assertEqual(parse_recency_date("2024-2025"), (2025, 12, 31))


if __name__ == "__main__":
    unittest.main()
