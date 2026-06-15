import argparse
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.job_creation.local_refiner import refine_job_with_local_edit
from scripts.job_creation.refinement_routes import LocalAction
from tests.test_refinement_router import router_context


class LocalRefinerTests(unittest.TestCase):
    def test_local_edit_writes_yaml_and_regenerates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            context = router_context()
            context.job_folder = Path(temp_dir)
            action = LocalAction(
                "set_job_config_field", field="include_coursework", value=True,
            )
            tex_path = Path(temp_dir) / "cv.tex"
            args = argparse.Namespace(compile_pdf=False, model="model")
            with patch("scripts.job_creation.local_refiner.generate_cv", return_value=tex_path) as generate:
                result, pages = refine_job_with_local_edit(args, context, "show coursework", action)
            job_config = yaml.safe_load((Path(temp_dir) / "job_config.yaml").read_text())
        self.assertEqual(result, tex_path)
        self.assertIsNone(pages)
        self.assertTrue(job_config["include_coursework"])
        self.assertEqual(generate.call_count, 1)


if __name__ == "__main__":
    unittest.main()
