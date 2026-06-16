import json
import unittest
from unittest.mock import patch

from scripts.telegram_bot.resolver.job_description_filter import tensorix_description_filter
from scripts.telegram_bot.resolver.visible_blocks import VisibleBlock


def block(index, text):
    return VisibleBlock(index, "div", text, 0)


class JobDescriptionFilterTests(unittest.TestCase):
    def test_tensorix_filter_returns_clean_description(self):
        payload = {
            "job_description": (
                "What you will accomplish\n"
                "Build and ship production-grade backend features that improve platform "
                "reliability and scalability.\n"
                "Contribute to distributed systems that process high-volume marketplace data.\n"
                "Improve service performance, throughput, observability, testing, debugging, "
                "automation, and operational efficiency for cloud-native platform services.\n\n"
                "What you will bring\n"
                "Proficiency in Java, Python, or C++ and working knowledge of SQL and NoSQL.\n"
                "Exposure to distributed systems, backend services, Kafka, Kubernetes, cloud "
                "platforms, and collaborative software engineering best practices.\n\n"
                "Recruiting Process\nCoding Assessment\nTechnical Interview\n\n"
                "Additional Details\nEqual opportunity employer."
            ),
            "confidence": 0.91,
            "reason": "removed LinkedIn chrome",
        }
        with patch(
            "scripts.telegram_bot.resolver.job_description_filter.tensorix_chat",
            return_value=json.dumps(payload),
        ) as chat:
            result = tensorix_description_filter(_blocks())
        self.assertIsNotNone(result.extraction)
        self.assertIn("Build and ship production-grade backend", result.extraction.text)
        self.assertIn("Coding Assessment", result.extraction.text)
        self.assertIn("model=minimax/minimax-m2.5", result.reason)
        self.assertEqual(chat.call_args.kwargs["model"], "minimax/minimax-m2.5")
        self.assertGreaterEqual(chat.call_args.kwargs["max_tokens"], 3000)

    def test_tensorix_filter_rejects_heading_only_description(self):
        payload = {
            "job_description": (
                "What you will accomplish\nWhat you will bring\nRecruiting Process\n"
                "Additional Details\nEqual opportunity employer."
            ),
            "confidence": 0.95,
            "reason": "bad extraction",
        }
        with patch(
            "scripts.telegram_bot.resolver.job_description_filter.tensorix_chat",
            return_value=json.dumps(payload),
        ):
            result = tensorix_description_filter(_blocks())
        self.assertIsNone(result.extraction)


def _blocks():
    texts = [
        "Sign in Join now",
        "What you will accomplish",
        "Build and ship production-grade backend features that improve reliability.",
        "What you will bring",
        "Strong foundation in Object-Oriented Programming and Java, Python, or C++.",
        "Working knowledge of SQL and NoSQL databases, testing, debugging, and automation.",
        "Exposure to distributed systems, backend services, Kafka, Kubernetes, and cloud platforms.",
        "Recruiting Process",
        "Coding Assessment",
        "Additional Details",
        "Equal opportunity employer.",
    ]
    return [block(index, text) for index, text in enumerate(texts)]


if __name__ == "__main__":
    unittest.main()
