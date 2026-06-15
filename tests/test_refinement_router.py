import json
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.career_schema import Selection
from scripts.job_creation.refine_context import RefineContext
from scripts.job_creation.refinement_router import route_refinement_feedback
from scripts.job_creation.refinement_routes import RefinementRouteKind
from tests.pdf_fixtures import minimal_database, minimal_job_config


def router_context() -> RefineContext:
    job_config = minimal_job_config()
    job_config.sections_order = ["education", "projects", "additional_information"]
    selection = Selection.model_validate({
        "projects": [{"id": "project_alpha", "bullets": ["p1"]}],
        "custom_sections": {"additional_information": ["item"]},
    })
    return RefineContext(
        Path("/tmp/job"), minimal_database(), job_config, selection,
        "Job description", "Requirements", "\\section{Projects}",
    )


class RefinementRouterTests(unittest.TestCase):
    def test_exact_fast_path_hides_coursework_without_planner(self):
        route = route_refinement_feedback("hide coursework", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.LOCAL_EDIT)
        self.assertEqual(route.local_action.field, "include_coursework")
        self.assertFalse(route.local_action.value)

    def test_compact_route_uses_tensorix_planner_json(self):
        payload = {"route": "compact_refinement", "confidence": 0.92, "reason": "wording only"}
        with patch.dict("os.environ", {"TENSORIX_API_KEY": "test"}, clear=True):
            with patch("scripts.job_creation.refinement_router.tensorix_chat", return_value=json.dumps(payload)):
                route = route_refinement_feedback("make it more concise", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.COMPACT_REFINEMENT)
        self.assertEqual(route.confidence, 0.92)

    def test_low_confidence_planner_falls_back_to_full_context(self):
        payload = {"route": "compact_refinement", "confidence": 0.2, "reason": "uncertain"}
        with patch.dict("os.environ", {"TENSORIX_API_KEY": "test"}, clear=True):
            with patch("scripts.job_creation.refinement_router.tensorix_chat", return_value=json.dumps(payload)):
                route = route_refinement_feedback("maybe improve it", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.FULL_CONTEXT_REFINEMENT)

    def test_invalid_planner_json_falls_back_to_full_context(self):
        with patch.dict("os.environ", {"TENSORIX_API_KEY": "test"}, clear=True):
            with patch("scripts.job_creation.refinement_router.tensorix_chat", return_value="not json"):
                route = route_refinement_feedback("polish the wording", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.FULL_CONTEXT_REFINEMENT)

    def test_valid_remove_selected_item_local_action(self):
        payload = {
            "route": "local_edit", "confidence": 0.95, "reason": "remove selected project",
            "local_action": {
                "type": "remove_selected_item", "item_kind": "projects",
                "item_id": "project_alpha",
            },
        }
        with patch.dict("os.environ", {"TENSORIX_API_KEY": "test"}, clear=True):
            with patch("scripts.job_creation.refinement_router.tensorix_chat", return_value=json.dumps(payload)):
                route = route_refinement_feedback("remove project_alpha", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.LOCAL_EDIT)
        self.assertEqual(route.local_action.item_id, "project_alpha")


if __name__ == "__main__":
    unittest.main()
