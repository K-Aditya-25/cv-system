import unittest
from unittest.mock import patch

from scripts.telegram_bot.resolver.block_scoring import BlockExtraction
from scripts.telegram_bot.resolver.boundary_planner import PlannedBoundary
from scripts.telegram_bot.resolver.extraction_fallback import fallback_extraction


class ResolverExtractionFallbackTests(unittest.TestCase):
    def test_uses_tensorix_job_filter_before_other_fallbacks(self):
        baseline = BlockExtraction("What you will accomplish\nWhat you will bring", 0.4, 0, 1, "base")
        text = (
            "What you will accomplish\nBuild and ship production-grade backend features that "
            "improve platform reliability and scalability while contributing to distributed "
            "systems that process high-volume marketplace data.\nWhat you will bring\nStrong "
            "Object-Oriented Programming fundamentals, Java or Python, SQL and NoSQL databases, "
            "testing, debugging, monitoring, automation, and cloud-native platform exposure."
        )
        filtered = PlannedBoundary(BlockExtraction(text, 0.9, 0, 4, "filter"), "filtered")
        with (
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_description_filter",
                  return_value=filtered),
            patch("scripts.telegram_bot.resolver.extraction_fallback.trafilatura_fallback") as traf,
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_boundary") as planner,
        ):
            result = fallback_extraction("<html></html>", [], "low confidence", baseline)
        self.assertEqual(result[0], "job-description-filter")
        traf.assert_not_called()
        planner.assert_not_called()

    def test_rejects_fallback_that_loses_deterministic_sections(self):
        baseline = BlockExtraction(
            "About the role\nWhat you will accomplish\nBuild reliable systems\n"
            "Improve service performance, throughput, and operational efficiency while "
            "strengthening observability through testing, monitoring, debugging, and automation. "
            "What you will bring\nPython and SQL with distributed backend fundamentals and "
            "cloud-native platform exposure.",
            0.45, 0, 3, "baseline",
        )
        fallback = PlannedBoundary(
            BlockExtraction(
                "About the role\nBuild reliable systems that improve platform reliability and "
                "scalability while collaborating with engineering and product partners on "
                "cloud-native platform services for high-volume marketplace data processing. "
                "Operate services at global scale with curiosity, ownership, and continuous "
                "learning in a collaborative engineering environment.",
                0.7, 0, 0, "fallback",
            ),
            "fallback extracted text",
        )
        with (
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_description_filter",
                  return_value=PlannedBoundary(None, "filter unavailable")),
            patch("scripts.telegram_bot.resolver.extraction_fallback.trafilatura_fallback",
                  return_value=fallback),
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_boundary",
                  return_value=PlannedBoundary(None, "planner unavailable")),
        ):
            result = fallback_extraction("<html></html>", [], "low confidence", baseline)
        self.assertIsNone(result)

    def test_rejects_boundary_output_with_empty_section_headings(self):
        baseline = BlockExtraction("What you will accomplish\nWhat you will bring", 0.4, 0, 1, "base")
        broken = (
            "Build and ship production-grade backend features that improve platform reliability "
            "and scalability. Contribute to distributed systems that process marketplace data. "
            "Improve testing, monitoring, debugging, automation, throughput, and efficiency. "
            "Bachelor's degree in Computer Science. Proficiency in Java, Python, or C++. "
            "Working knowledge of SQL and NoSQL databases. Coding Assessment. Technical "
            "Interview. About The Team And The Role. The platform team builds data systems. "
            "What you will accomplish\nWhat you will bring\nRecruiting Process\nAdditional Details"
        )
        boundary = PlannedBoundary(BlockExtraction(broken, 1.0, 0, 10, "planner"), "planned")
        with (
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_description_filter",
                  return_value=PlannedBoundary(None, "filter unavailable")),
            patch("scripts.telegram_bot.resolver.extraction_fallback.trafilatura_fallback",
                  return_value=PlannedBoundary(None, "trafilatura unavailable")),
            patch("scripts.telegram_bot.resolver.extraction_fallback.tensorix_boundary",
                  return_value=boundary),
        ):
            result = fallback_extraction("<html></html>", [], "low confidence", baseline)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
