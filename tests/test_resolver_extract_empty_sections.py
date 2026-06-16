import unittest
from unittest.mock import patch

from scripts.telegram_bot.resolver.extract import ExtractionError, extract_job


class ResolverExtractEmptySectionTests(unittest.TestCase):
    def test_rejects_low_confidence_empty_headings_when_fallbacks_fail(self):
        html = """
        <html><body><main>
        <p>Build and ship production-grade backend features that improve platform reliability
        and scalability for distributed marketplace data systems. Contribute to high-volume
        data processing, service performance, observability, testing, debugging, automation,
        cloud-native services, SQL, NoSQL, Kafka, Kubernetes, and collaborative engineering.
        About The Team And The Role The Cloud Data Technologies organization builds core
        infrastructure for analytics and experimentation at global scale.
        What you will accomplish What you will bring Recruiting Process Additional Details
        eBay is an equal opportunity employer.</p>
        </main></body></html>
        """
        with patch("scripts.telegram_bot.resolver.extract.fallback_extraction", return_value=None):
            with self.assertRaisesRegex(ExtractionError, "empty job section headings"):
                extract_job(html)


if __name__ == "__main__":
    unittest.main()
