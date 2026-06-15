import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.career_schema import Selection
from scripts.create_job_from_description import enforce_one_page_pdf
from tests.pdf_fixtures import llm_payload, minimal_database, minimal_job_config


class PdfCallBudgetTests(unittest.TestCase):
    def test_compile_pdf_workflow_allows_only_one_automatic_revision_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder, tex_path = Path(temp_dir), Path(temp_dir) / "target_engineer.tex"
            with (
                patch("scripts.create_job_from_description.compile_pdf_and_count_pages", side_effect=[2, 2, 2]),
                patch("scripts.create_job_from_description.generate_cv", return_value=tex_path),
                patch("scripts.create_job_from_description.call_anthropic", return_value=llm_payload()) as call_mock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                result_tex_path, page_count = enforce_one_page_pdf(
                    job_folder=job_folder, database=minimal_database(), job_description="Job",
                    cv_requirements="Requirements", candidate_inventory="Inventory",
                    system_prompt="System", model="model", job_config=minimal_job_config(),
                    selection=Selection(), tex_path=tex_path,
                )
            self.assertEqual(result_tex_path, tex_path)
            self.assertEqual(page_count, 2)
            self.assertEqual(call_mock.call_count, 1)
