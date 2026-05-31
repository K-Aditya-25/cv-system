import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.career_schema import JobConfig, Selection
from scripts.create_job_from_description import enforce_one_page_pdf
from tests.pdf_fixtures import minimal_database, minimal_job_config


class PdfLayoutFallbackTests(unittest.TestCase):
    def test_compact_margin_fallback_runs_before_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder, tex_path, job_config = Path(temp_dir), Path(temp_dir) / "cv.tex", minimal_job_config()
            with (
                patch("scripts.create_job_from_description.compile_pdf_and_count_pages", side_effect=[2, 1]),
                patch("scripts.create_job_from_description.generate_cv", return_value=tex_path) as generate_mock,
                patch("scripts.create_job_from_description.call_anthropic") as call_mock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                _, page_count = enforce_one_page_pdf(
                    job_folder=job_folder, database=minimal_database(), job_description="Job",
                    cv_requirements="Requirements", candidate_inventory="Inventory",
                    system_prompt="System", model="model", job_config=job_config,
                    selection=Selection(), tex_path=tex_path,
                )
            self.assertEqual(page_count, 1)
            self.assertEqual(job_config.page_margin, "0.275in")
            self.assertEqual(generate_mock.call_count, 1)
            call_mock.assert_not_called()

    def test_additional_information_removal_runs_before_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder, tex_path = Path(temp_dir), Path(temp_dir) / "cv.tex"
            config = JobConfig.model_validate({
                "company": "Target", "role": "Engineer", "output_name": "target_engineer",
                "sections_order": ["education", "additional_information", "skills"],
            })
            selection = Selection.model_validate({"custom_sections": {"additional_information": ["work_authorization"]}})
            with (
                patch("scripts.create_job_from_description.compile_pdf_and_count_pages", side_effect=[2, 2, 1]),
                patch("scripts.create_job_from_description.generate_cv", return_value=tex_path) as generate_mock,
                patch("scripts.create_job_from_description.call_anthropic") as call_mock,
                contextlib.redirect_stdout(io.StringIO()),
            ):
                _, page_count = enforce_one_page_pdf(
                    job_folder=job_folder, database=minimal_database(), job_description="Job",
                    cv_requirements="Requirements", candidate_inventory="Inventory",
                    system_prompt="System", model="model", job_config=config, selection=selection,
                    tex_path=tex_path,
                )
            self.assertEqual(page_count, 1)
            self.assertEqual(config.sections_order, ["education", "skills"])
            self.assertEqual(selection.custom_sections, {})
            self.assertEqual(generate_mock.call_count, 2)
            call_mock.assert_not_called()
