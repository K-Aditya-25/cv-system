import json
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.job_creation.refinement_router import route_refinement_feedback
from tests.test_refinement_router import router_context

FIXTURE = Path(__file__).parent / "fixtures" / "refinement_router_cases.yaml"


class RefinementRouterEvalTests(unittest.TestCase):
    def test_router_eval_cases(self):
        for case in yaml.safe_load(FIXTURE.read_text(encoding="utf-8")):
            with self.subTest(case=case["name"]):
                payload = case.get("planner_payload") or {
                    "route": "full_context_refinement",
                    "confidence": 0.8,
                    "reason": "mock planner fallback",
                }
                with patch(
                    "scripts.job_creation.refinement_router.tensorix_chat",
                    return_value=json.dumps(payload),
                ) as planner:
                    route = route_refinement_feedback(case["feedback"], router_context())

                self.assertEqual(route.kind.value, case["expected_route"])
                self.assertEqual(planner.call_count, int(case["expect_planner_call"]))
                self._assert_local_action(route.local_action, case.get("expected_local_action"))

    def _assert_local_action(self, action, expected):
        if not expected:
            self.assertIsNone(action)
            return
        self.assertIsNotNone(action)
        for key, value in expected.items():
            self.assertEqual(getattr(action, key), value)


if __name__ == "__main__":
    unittest.main()
