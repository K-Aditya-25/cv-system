import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.debug_refinement_route import main


class DebugRefinementRouteTests(unittest.TestCase):
    def test_debug_route_prints_diagnostics_without_planner(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            master = root / "master.yaml"
            job = root / "job"
            job.mkdir()
            master.write_text("profile:\n  name: Alex\n  email: alex@example.com\n", encoding="utf-8")
            (job / "job_description.md").write_text("Job\n", encoding="utf-8")
            (job / "job_config.yaml").write_text(
                "company: Target\nrole: Engineer\noutput_name: target_engineer\n",
                encoding="utf-8",
            )
            selection = "skills:\n  testing_quality:\n  - Functional Testing\n"
            selection_path = job / "selection.yaml"
            selection_path.write_text(selection, encoding="utf-8")

            output = io.StringIO()
            argv = ["debug_refinement_route.py", str(job), "Remove Testing Quality from skills",
                    "--master-data", str(master)]
            with (
                patch.object(sys, "argv", argv),
                patch("scripts.job_creation.refinement_router.tensorix_chat") as planner,
                contextlib.redirect_stdout(output),
            ):
                exit_code = main()

            self.assertEqual(exit_code, 0)
            self.assertEqual(planner.call_count, 0)
            self.assertEqual(selection_path.read_text(encoding="utf-8"), selection)
            self.assertIn("route: local_edit", output.getvalue())
            self.assertIn("claude_required: false", output.getvalue())
            self.assertIn("field: testing_quality", output.getvalue())


if __name__ == "__main__":
    unittest.main()
