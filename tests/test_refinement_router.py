import json
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.career_schema import CareerDatabase, Selection
from scripts.job_creation.refine_context import RefineContext
from scripts.job_creation.refinement_router import route_refinement_feedback
from scripts.job_creation.refinement_routes import RefinementRouteKind
from tests.pdf_fixtures import minimal_job_config


def router_context() -> RefineContext:
    job_config = minimal_job_config()
    job_config.sections_order = ["education", "projects", "additional_information"]
    database = CareerDatabase.model_validate({
        "profile": {"name": "Alex Example", "email": "alex@example.com"},
        "projects": [
            {"id": "project_alpha", "name": "Project Alpha"},
            {"id": "dublin_bus_route_finder", "name": "Dublin Bus Route Finder"},
        ],
    })
    selection = Selection.model_validate({
        "projects": [
            {"id": "project_alpha", "bullets": ["p1"]},
            {"id": "dublin_bus_route_finder", "bullets": ["p1"]},
        ],
        "skills": {"testing_quality": ["Functional Testing"]},
        "custom_sections": {"additional_information": ["item"]},
    })
    return RefineContext(
        Path("/tmp/job"), database, job_config, selection,
        "Job description", "Requirements", "\\section{Projects}",
    )


class RefinementRouterTests(unittest.TestCase):
    def test_exact_fast_path_hides_coursework_without_planner(self):
        route = route_refinement_feedback("hide coursework", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.LOCAL_EDIT)
        self.assertEqual(route.local_action.field, "include_coursework")
        self.assertFalse(route.local_action.value)

    def test_exact_fast_path_removes_skill_category_without_planner(self):
        with patch("scripts.job_creation.refinement_router.tensorix_chat") as planner:
            route = route_refinement_feedback("Remove Testing Quality from skills", router_context())
        self.assertEqual(route.kind, RefinementRouteKind.LOCAL_EDIT)
        self.assertEqual(route.local_action.type, "remove_skill_category")
        self.assertEqual(route.local_action.field, "testing_quality")
        self.assertEqual(planner.call_count, 0)

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

    def test_project_replacement_feedback_forces_full_context_without_planner(self):
        feedback = (
            "Add the CV system project and remove the Dublin Bus Finder project. "
            "Focus on software engineering aspects of the experience, projects, and skills."
        )
        with patch("scripts.job_creation.refinement_router.tensorix_chat") as planner:
            route = route_refinement_feedback(feedback, router_context())
        self.assertEqual(route.kind, RefinementRouteKind.FULL_CONTEXT_REFINEMENT)
        self.assertEqual(planner.call_count, 0)

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
