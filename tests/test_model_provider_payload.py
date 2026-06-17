import unittest
from unittest.mock import patch

from scripts.job_creation.claude_payload import call_model_for_valid_payload
from scripts.job_creation.model_catalog import resolve_model_choice
from tests.pdf_fixtures import llm_payload, minimal_database


class ModelProviderPayloadTests(unittest.TestCase):
    def test_tensorix_provider_uses_tensorix_chat_for_valid_payload(self):
        with patch("scripts.job_creation.model_call.tensorix_chat", return_value=llm_payload()) as chat:
            payload, job_config, _, _ = call_model_for_valid_payload(
                system_prompt="System",
                user_prompt="User",
                provider="tensorix",
                model="z-ai/glm-5.2",
                database=minimal_database(),
                allow_longer_cv=False,
            )
        self.assertEqual(job_config.company, "Target")
        self.assertEqual(payload["job_summary_text"], "Target engineer role.")
        self.assertEqual(chat.call_args.kwargs["model"], "z-ai/glm-5.2")
        self.assertEqual(chat.call_args.kwargs["purpose"], "Tensorix CV model")

    def test_model_catalog_resolves_numbered_tensorix_choices(self):
        self.assertEqual(resolve_model_choice("2").key, "glm")
        self.assertEqual(resolve_model_choice("kimi").key, "kimi")
        self.assertIsNone(resolve_model_choice("tensorix"))


if __name__ == "__main__":
    unittest.main()
