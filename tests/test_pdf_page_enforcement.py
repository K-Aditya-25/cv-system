import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.create_job_from_description import (
    IntakeError,
    assert_pdf_is_exactly_one_page,
    build_one_page_enforcement_feedback,
    halve_margin,
)


class PdfPageEnforcementTests(unittest.TestCase):
    def test_exact_one_page_assertion_rejects_two_pages(self) -> None:
        with patch("scripts.create_job_from_description.count_pdf_pages", return_value=2):
            with self.assertRaisesRegex(IntakeError, "expected exactly 1 page"):
                assert_pdf_is_exactly_one_page(Path("cv.pdf"))

    def test_halve_margin_preserves_unit(self) -> None:
        self.assertEqual(halve_margin("0.55in"), "0.275in")
        self.assertEqual(halve_margin("1cm"), "0.5cm")

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


if __name__ == "__main__":
    unittest.main()
