from scripts.telegram_bot.models import Session
from scripts.telegram_bot.resolver_models import ResolutionRequest
from tests.telegram_controller_fixtures import ControllerTestCase, update


class TelegramResolverControllerTests(ControllerTestCase):
    def test_url_only_intake_queues_background_resolution(self):
        self.controller.handle(update("/new"))
        self.controller.handle(update("https://linkedin.example/jobs/42"))
        item, session = self.work.get_nowait(), self.store.session(42)
        request = ResolutionRequest.from_json(item.payload)
        self.assertEqual((item.operation, session.state), ("resolve_url", "resolving_job_url"))
        self.assertEqual((request.url, request.mode), ("https://linkedin.example/jobs/42", "automatic"))
        self.assertEqual(item.request_id, session.request_id)

    def test_explicit_careers_retry_preserves_original_url(self):
        self.store.save(Session(42, state="awaiting_careers_url", session_active=1,
                                job_url="https://linkedin.example/jobs/42"))
        self.controller.handle(update("https://careers.example/jobs/42"))
        item, session = self.work.get_nowait(), self.store.session(42)
        request = ResolutionRequest.from_json(item.payload)
        self.assertEqual((request.url, request.mode), ("https://careers.example/jobs/42", "explicit"))
        self.assertEqual(session.job_url, "https://linkedin.example/jobs/42")

    def test_pasted_text_is_fallback_after_failed_url(self):
        self.store.save(Session(42, state="awaiting_careers_url", session_active=1,
                                job_url="https://linkedin.example/jobs/42"))
        self.controller.handle(update("Full pasted job description"))
        session = self.store.session(42)
        self.assertEqual((session.state, session.description),
                         ("collecting_description", "Full pasted job description"))
        self.assertEqual((session.job_url, session.careers_url), ("", ""))

    def test_text_file_is_fallback_after_failed_url(self):
        self.store.save(Session(42, state="awaiting_careers_url", session_active=1,
                                job_url="https://linkedin.example/jobs/42"))
        self.controller.handle(update(document={"file_name": "role.txt", "file_id": "file-1"}))
        session = self.store.session(42)
        self.assertEqual((session.state, session.description),
                         ("collecting_description", "downloaded file-1"))

    def test_http_url_is_not_queued_for_public_https_resolver(self):
        self.controller.handle(update("/new"))
        self.controller.handle(update("http://jobs.example/42"))
        self.assertTrue(self.work.empty())
        self.assertEqual(self.store.session(42).description, "http://jobs.example/42")

    def test_cancel_invalidates_inflight_url_result(self):
        self.controller.handle(update("/new"))
        self.controller.handle(update("https://jobs.example/42"))
        item = self.work.get_nowait()
        self.controller.handle(update("/cancel"))
        self.assertNotEqual(self.store.session(42).request_id, item.request_id)


if __name__ == "__main__":
    import unittest
    unittest.main()
