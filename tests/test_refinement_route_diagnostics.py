import unittest

from scripts.job_creation.refinement_route_diagnostics import (
    format_route_cli,
    format_route_log,
    route_diagnostics,
)
from scripts.job_creation.refinement_routes import LOCAL_CONTEXT, LocalAction, RefinementRoute
from scripts.job_creation.refinement_routes import RefinementRouteKind


class RefinementRouteDiagnosticsTests(unittest.TestCase):
    def test_formats_local_route_data_for_logging_and_cli(self):
        route = RefinementRoute(
            RefinementRouteKind.LOCAL_EDIT,
            "exact command to remove skills.testing_quality",
            LOCAL_CONTEXT,
            local_action=LocalAction("remove_skill_category", field="testing_quality"),
        )
        data = route_diagnostics(route)
        self.assertEqual(data["route"], "local_edit")
        self.assertFalse(data["claude_required"])
        self.assertEqual(data["required_context"], ["job_config.yaml", "selection.yaml"])
        self.assertEqual(data["local_action"]["field"], "testing_quality")

        log_line = format_route_log(route)
        self.assertIn("[refinement.route] route=local_edit", log_line)
        self.assertIn("claude_required=false", log_line)
        self.assertIn("action=remove_skill_category", log_line)
        self.assertIn("field=testing_quality", log_line)

        cli = format_route_cli(route)
        self.assertIn("route: local_edit", cli)
        self.assertIn("claude_required: false", cli)
        self.assertIn("  field: testing_quality", cli)


if __name__ == "__main__":
    unittest.main()
