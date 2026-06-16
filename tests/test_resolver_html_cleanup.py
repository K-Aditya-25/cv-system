import json
import unittest
from unittest.mock import patch

from scripts.telegram_bot.resolver.extract import extract_job
from scripts.telegram_bot.resolver.job_description_filter import tensorix_description_filter


class ResolverHtmlCleanupTests(unittest.TestCase):
    def test_cleans_escaped_html_from_json_ld_description(self):
        body = (
            "At eBay&lt;br&gt;&lt;strong&gt;What you will accomplish&lt;/strong&gt;"
            "&lt;ul&gt;&lt;li&gt;Build production-grade backend services that improve "
            "reliability, scalability, throughput, observability, testing, debugging, and "
            "automation for distributed marketplace data platforms.&lt;/li&gt;&lt;li&gt;"
            "Collaborate with product and engineering partners on cloud-native services, "
            "SQL, NoSQL, Kafka, Kubernetes, and operational quality.&lt;/li&gt;&lt;/ul&gt;"
            "&lt;strong&gt;What you will bring&lt;/strong&gt;&lt;ul&gt;&lt;li&gt;Java, Python, "
            "or C++ with strong software engineering fundamentals and problem-solving skills."
            "&lt;/li&gt;&lt;/ul&gt;"
        )
        payload = {"@type": "JobPosting", "title": "Graduate SWE", "description": body}
        html = f'<script type="application/ld+json">{json.dumps(payload)}</script>'
        job = extract_job(f"<html><body>{html}</body></html>")
        self.assertEqual(job.method, "json-ld")
        self.assertIn("What you will accomplish", job.description)
        self.assertNotIn("<br>", job.description)
        self.assertNotIn("<li>", job.description)

    def test_tensorix_filter_strips_html_tags_from_output(self):
        payload = {"job_description": _html_description(), "confidence": 0.9, "reason": "cleaned"}
        with patch(
            "scripts.telegram_bot.resolver.job_description_filter.tensorix_chat",
            return_value=json.dumps(payload),
        ):
            result = tensorix_description_filter(_blocks())
        self.assertIsNotNone(result.extraction)
        self.assertNotIn("<li>", result.extraction.text)
        self.assertNotIn("<br>", result.extraction.text)


def _html_description():
    return (
        "What you will accomplish<br><ul><li>Build production-grade backend services that "
        "improve reliability, scalability, throughput, observability, testing, debugging, and "
        "automation for distributed marketplace data platforms.</li><li>Collaborate with "
        "product and engineering partners on cloud-native services, SQL, NoSQL, Kafka, "
        "Kubernetes, and operational quality.</li></ul><strong>What you will bring</strong>"
        "<ul><li>Java, Python, or C++ with strong software engineering fundamentals, database "
        "knowledge, distributed systems exposure, and problem-solving skills.</li></ul>"
    )


def _blocks():
    return [type("Block", (), {"index": 0, "text": _html_description()})()]


if __name__ == "__main__":
    unittest.main()
