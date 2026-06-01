import tempfile
import unittest
from pathlib import Path
from queue import Queue
from unittest.mock import patch

from scripts.telegram_bot.models import Session, WorkItem
from scripts.telegram_bot.resolver_models import ExtractedPosting, JobMetadata, ResolutionResult
from scripts.telegram_bot.runtime import BotRuntime
from scripts.telegram_bot.runtime_url import _browser, apply_result
from scripts.telegram_bot.store import StateStore


class Api:
    def __init__(self):
        self.messages = []

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


class TelegramResolverRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = StateStore(Path(self.temp.name) / "state.sqlite3")
        self.runtime = object.__new__(BotRuntime)
        self.runtime.store, self.runtime.api, self.runtime.work = self.store, Api(), Queue()

    def tearDown(self):
        self.temp.cleanup()

    def item(self, request_id=3):
        return WorkItem(42, "resolve_url", "{}", request_id)

    def save_resolving(self, request_id=3):
        self.store.save(Session(42, state="resolving_job_url", pending_operation="resolve_url",
                                request_id=request_id, session_active=1))

    def test_resolved_description_advances_to_instructions(self):
        self.save_resolving()
        posting = ExtractedPosting("full role", JobMetadata(company="Acme", role="Engineer"),
                                   "https://jobs.example/42")
        apply_result(self.runtime, self.item(), ResolutionResult("resolved", posting=posting))
        session = self.store.session(42)
        self.assertEqual((session.state, session.description), ("collecting_instructions", "full role"))
        self.assertIn("Acme - Engineer", self.runtime.api.messages[-1][1])

    def test_automatic_failure_requests_explicit_careers_url(self):
        self.save_resolving()
        apply_result(self.runtime, self.item(), ResolutionResult("needs_explicit_link"))
        self.assertEqual(self.store.session(42).state, "awaiting_careers_url")
        self.assertIn("careers-page URL", self.runtime.api.messages[-1][1])

    def test_explicit_failure_returns_to_paste_fallback(self):
        self.save_resolving()
        apply_result(self.runtime, self.item(), ResolutionResult("fallback_text"))
        self.assertEqual(self.store.session(42).state, "collecting_description")
        self.assertIn("Paste the job description", self.runtime.api.messages[-1][1])

    def test_stale_resolution_result_is_ignored(self):
        self.save_resolving(request_id=4)
        apply_result(self.runtime, self.item(request_id=3), ResolutionResult("fallback_text"))
        self.assertEqual(self.store.session(42).state, "resolving_job_url")
        self.assertEqual(self.runtime.api.messages, [])

    def test_browser_adapter_is_enabled_only_by_explicit_flag(self):
        with patch("scripts.telegram_bot.runtime_url.get_env_secret", return_value=None):
            self.assertIsNone(_browser())
        with patch("scripts.telegram_bot.runtime_url.get_env_secret", return_value="1"):
            self.assertTrue(_browser().config.enabled)


if __name__ == "__main__":
    unittest.main()
