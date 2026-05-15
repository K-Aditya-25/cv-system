from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from schemas.career_schema import CareerDatabase, JobConfig, Selection
from scripts.create_job_from_description import (
    IntakeError,
    assert_pdf_is_exactly_one_page,
    build_one_page_enforcement_feedback,
    enforce_one_page_pdf,
    halve_margin,
)


def minimal_database() -> CareerDatabase:
    return CareerDatabase.model_validate(
        {"profile": {"name": "Alex Example", "email": "alex@example.com"}}
    )


def minimal_job_config() -> JobConfig:
    return JobConfig.model_validate(
        {"company": "Target", "role": "Engineer", "output_name": "target_engineer"}
    )


def llm_payload() -> str:
    return json.dumps(
        {
            "job_config": {
                "company": "Target",
                "role": "Engineer",
                "location": None,
                "cv_length": "one_page",
                "cv_variant": "general",
                "target_profile": None,
                "output_name": "target_engineer",
                "template": "cv_template.tex.j2",
                "sections_order": ["education", "experience", "projects", "skills"],
                "include_coursework": False,
                "include_education_bullets": False,
                "show_experience_technologies": False,
                "show_project_technologies": False,
                "page_margin": None,
            },
            "selection": {},
            "job_summary_text": "Target engineer role.",
            "selection_rationale": ["Reduced content for a one-page CV."],
        }
    )


class PdfPageEnforcementTests(unittest.TestCase):
    def test_exact_one_page_assertion_rejects_two_pages(self) -> None:
        with patch("scripts.create_job_from_description.count_pdf_pages", return_value=2):
            with self.assertRaisesRegex(IntakeError, "expected exactly 1 page"):
                assert_pdf_is_exactly_one_page(Path("cv.pdf"))

    def test_halve_margin_preserves_unit(self) -> None:
        self.assertEqual(halve_margin("0.55in"), "0.275in")
        self.assertEqual(halve_margin("1cm"), "0.5cm")

    def test_compact_margin_fallback_runs_before_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder = Path(temp_dir)
            tex_path = job_folder / "target_engineer.tex"
            job_config = minimal_job_config()

            with (
                patch(
                    "scripts.create_job_from_description.compile_pdf_and_count_pages",
                    side_effect=[2, 1],
                ),
                patch(
                    "scripts.create_job_from_description.generate_cv",
                    return_value=tex_path,
                ) as generate_mock,
                patch("scripts.create_job_from_description.call_anthropic") as call_mock,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    _, page_count = enforce_one_page_pdf(
                        job_folder=job_folder,
                        database=minimal_database(),
                        job_description="Job description",
                        cv_requirements="Requirements",
                        candidate_inventory="Inventory",
                        system_prompt="System",
                        model="model",
                        job_config=job_config,
                        selection=Selection(),
                        tex_path=tex_path,
                    )

            self.assertEqual(page_count, 1)
            self.assertEqual(job_config.page_margin, "0.275in")
            self.assertEqual(generate_mock.call_count, 1)
            call_mock.assert_not_called()

    def test_additional_information_removal_runs_before_llm(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder = Path(temp_dir)
            tex_path = job_folder / "target_engineer.tex"
            job_config = JobConfig.model_validate(
                {
                    "company": "Target",
                    "role": "Engineer",
                    "output_name": "target_engineer",
                    "sections_order": ["education", "additional_information", "skills"],
                }
            )
            selection = Selection.model_validate(
                {"custom_sections": {"additional_information": ["work_authorization"]}}
            )

            with (
                patch(
                    "scripts.create_job_from_description.compile_pdf_and_count_pages",
                    side_effect=[2, 2, 1],
                ),
                patch(
                    "scripts.create_job_from_description.generate_cv",
                    return_value=tex_path,
                ) as generate_mock,
                patch("scripts.create_job_from_description.call_anthropic") as call_mock,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    _, page_count = enforce_one_page_pdf(
                        job_folder=job_folder,
                        database=minimal_database(),
                        job_description="Job description",
                        cv_requirements="Requirements",
                        candidate_inventory="Inventory",
                        system_prompt="System",
                        model="model",
                        job_config=job_config,
                        selection=selection,
                        tex_path=tex_path,
                    )

            self.assertEqual(page_count, 1)
            self.assertEqual(job_config.sections_order, ["education", "skills"])
            self.assertEqual(selection.custom_sections, {})
            self.assertEqual(generate_mock.call_count, 2)
            call_mock.assert_not_called()

    def test_llm_feedback_mentions_prior_layout_and_section_fallbacks(self) -> None:
        feedback = build_one_page_enforcement_feedback(
            page_count=2,
            attempt=1,
            compact_margin="0.275in",
            removed_additional_information=True,
        )

        self.assertIn("page margin to 0.275in", feedback)
        self.assertIn("removed the additional_information section", feedback)
        self.assertIn("absolutely necessary", feedback)

    def test_compile_pdf_workflow_allows_only_one_automatic_revision_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            job_folder = Path(temp_dir)
            tex_path = job_folder / "target_engineer.tex"

            with (
                patch(
                    "scripts.create_job_from_description.compile_pdf_and_count_pages",
                    side_effect=[2, 2, 2],
                ),
                patch(
                    "scripts.create_job_from_description.generate_cv",
                    return_value=tex_path,
                ),
                patch(
                    "scripts.create_job_from_description.call_anthropic",
                    return_value=llm_payload(),
                ) as call_mock,
            ):
                with contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(IntakeError, "2 total LLM calls"):
                        enforce_one_page_pdf(
                            job_folder=job_folder,
                            database=minimal_database(),
                            job_description="Job description",
                            cv_requirements="Requirements",
                            candidate_inventory="Inventory",
                            system_prompt="System",
                            model="model",
                            job_config=minimal_job_config(),
                            selection=Selection(),
                            tex_path=tex_path,
                        )

            self.assertEqual(call_mock.call_count, 1)


if __name__ == "__main__":
    unittest.main()
