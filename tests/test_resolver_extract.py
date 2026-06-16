import io
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.telegram_bot.resolver.boundary_planner import PlannedBoundary
from scripts.telegram_bot.resolver.extract import ExtractionError, extract_job

FIXTURES = Path(__file__).parent / "fixtures" / "resolver"


def fixture(name):
    return (FIXTURES / name).read_text(encoding="utf-8")


class ResolverExtractTests(unittest.TestCase):
    def test_extracts_linkedin_style_json_ld(self):
        job = extract_job(fixture("linkedin_job.html"))
        self.assertEqual((job.title, job.company, job.location),
                         ("Senior Platform Engineer", "Acme Cloud", "Dublin"))
        self.assertEqual(job.method, "json-ld")
        self.assertIn("Build reliable distributed platform services", job.description)

    def test_extracts_visible_html_when_structured_data_is_absent(self):
        job = extract_job(fixture("visible_job.html"))
        self.assertEqual(job.method, "dom-score")
        self.assertIn("dependable backend services", job.description)

    def test_rejects_blocked_or_thin_pages(self):
        with self.assertRaises(ExtractionError):
            extract_job(fixture("blocked.html"))

    def test_cleans_linkedin_tail_from_visible_job_text(self):
        with patch(
            "scripts.telegram_bot.resolver.extraction_fallback.tensorix_description_filter",
            return_value=PlannedBoundary(None, "filter disabled in deterministic extraction test"),
        ):
            job = extract_job(fixture("linkedin_ebay_visible.html"))
        self.assertIn("At eBay, we're more than a global ecommerce leader", job.description)
        self.assertIn("What you will bring", job.description)
        self.assertIn("Recruiting Process", job.description)
        self.assertIn("Additional Details", job.description)
        self.assertNotIn("Join to apply", job.description)
        self.assertNotIn("Direct message the job poster", job.description)
        self.assertNotIn("Similar jobs", job.description)
        self.assertNotIn("People also viewed", job.description)
        self.assertNotIn("LinkedIn ©", job.description)

    def test_keeps_split_linkedin_section_bullets_when_fallbacks_fail(self):
        with patch("scripts.telegram_bot.resolver.extract.fallback_extraction", return_value=None):
            job = extract_job(fixture("linkedin_ebay_split_sections.html"))
        self.assertEqual(job.method, "dom-score-low-confidence")
        self.assertIn("What you will accomplish", job.description)
        self.assertIn("Build and ship production-grade backend features", job.description)
        self.assertIn("What you will bring", job.description)
        self.assertIn("Proficiency in Java, Python, or C++", job.description)
        self.assertIn("Recruiting Process", job.description)
        self.assertIn("Coding Assessment", job.description)
        self.assertIn("Additional Details", job.description)
        self.assertIn("We use cookies to enhance your experience", job.description)
        self.assertNotIn("Seniority level", job.description)

    def test_cleans_collapsed_linkedin_chrome_without_dropping_responsibilities(self):
        html = """
        <html><body><p>
        This button displays the currently selected search type. When expanded it provides
        a list of search options that will switch the search inputs to match the current
        selection. Graduate SWE - Data Platforms Dublin, County Dublin, Ireland Join to
        apply for the Graduate SWE - Data Platforms role at eBay Graduate SWE - Data
        Platforms Build and ship production-grade backend features that improve platform
        reliability and scalability. At eBay, we're more than a global ecommerce leader.
        What you will bring Proficiency in Java, Python, or C++. Additional Details eBay
        is an equal opportunity employer. Similar jobs Software Engineer Dublin.
        </p></body></html>
        """
        job = extract_job(html)
        self.assertIn("Build and ship production-grade backend features", job.description)
        self.assertIn("What you will bring", job.description)
        self.assertNotIn("This button displays", job.description)
        self.assertNotIn("Join to apply", job.description)
        self.assertNotIn("Similar jobs", job.description)

    def test_logs_extraction_decisions_to_backend_stdout(self):
        output = io.StringIO()
        with redirect_stdout(output):
            extract_job(fixture("visible_job.html"))
        self.assertIn("[resolver.extract] dom-score candidate", output.getvalue())
        self.assertIn("[resolver.extract] using dom-score extraction", output.getvalue())


if __name__ == "__main__":
    unittest.main()
