import unittest

from scripts.generate_cv import build_render_context, parse_recency_date
from tests.recency_fixtures import database, job_config, selection


class RecencyOrderingTests(unittest.TestCase):
    def test_generated_context_orders_experience_and_projects_by_recency(self) -> None:
        context = build_render_context(database(), job_config(), selection())
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
