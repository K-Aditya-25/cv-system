import unittest
from pathlib import Path

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
        self.assertEqual(job.method, "html")
        self.assertIn("dependable backend services", job.description)

    def test_rejects_blocked_or_thin_pages(self):
        with self.assertRaises(ExtractionError):
            extract_job(fixture("blocked.html"))


if __name__ == "__main__":
    unittest.main()
