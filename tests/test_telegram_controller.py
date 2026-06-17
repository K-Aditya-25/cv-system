from pathlib import Path
from unittest.mock import patch

from scripts.telegram_bot.job_catalog import JobChoice
from scripts.telegram_bot.models import Session
from tests.telegram_controller_fixtures import ControllerTestCase, update


class TelegramControllerTests(ControllerTestCase):

    def test_whoami_is_available_before_whitelisting(self):
        self.controller.handle(update("/whoami", chat_id=99))
        self.assertIn("99", self.api.messages[-1][1])

    def test_chunks_and_none_enqueue_generation(self):
        for text in ("/new", "first", "second", "/done", "2", "/none"):
            self.controller.handle(update(text))
        item = self.work.get_nowait()
        self.assertEqual(item.operation, "create")
        self.assertIn("first\\n\\nsecond", item.payload)
        self.assertIn('"model_key": "glm"', item.payload)
        self.assertEqual(self.store.session(42).state, "busy")

    def test_text_file_adds_description_chunk(self):
        self.controller.handle(update("/new"))
        self.controller.handle(update(document={"file_name": "role.txt", "file_id": "file-1"}))
        self.assertEqual(self.store.session(42).description, "downloaded file-1")

    def test_invalid_text_file_is_rejected_without_changing_draft(self):
        self.controller.handle(update("/new"))
        self.api.download_text = lambda _file_id: (_ for _ in ()).throw(ValueError("too large"))
        self.controller.handle(update(document={"file_name": "role.txt", "file_id": "file-1"}))
        self.assertEqual(self.store.session(42).description, "")
        self.assertIn("Could not read", self.api.messages[-1][1])

    def test_busy_text_is_combined_as_queued_feedback(self):
        self.store.save(Session(42, state="busy", session_active=1))
        self.controller.handle(update("shorter"))
        self.controller.handle(update("focus Python"))
        self.assertEqual(self.store.session(42).queued_feedback, "shorter\n\nfocus Python")

    def test_active_session_repairs_missing_folder_for_refinement(self):
        self.store.save(Session(42, latest_pdf="/jobs/acme/cv.pdf", session_active=1))
        self.controller.handle(update("discard the Hashnode link"))
        item = self.work.get_nowait()
        self.assertEqual(item.operation, "refine")
        self.assertEqual(self.store.session(42).active_job_folder, "/jobs/acme")

    def test_idle_text_after_restart_requires_new(self):
        self.store.save(Session(42, latest_pdf="/jobs/acme/cv.pdf"))
        self.controller.handle(update("discard the Hashnode link"))
        self.assertTrue(self.work.empty())
        self.assertIn("Use /new", self.api.messages[-1][1])

    def test_refine_command_selects_existing_cv_before_feedback(self):
        job = JobChoice(Path("/jobs/acme"), Path("/jobs/acme/cv.pdf"), "Acme - Engineer")
        with patch("scripts.telegram_bot.controller_jobs.available_jobs", return_value=[job]):
            self.controller.handle(update("/refine"))
            self.controller.handle(update("1"))
            self.controller.handle(update("remove Hashnode"))
        session, item = self.store.session(42), self.work.get_nowait()
        self.assertEqual(session.active_job_folder, "/jobs/acme")
        self.assertEqual(item.operation, "refine")

    def test_cancel_discards_recovery_and_queued_feedback(self):
        self.store.save(Session(42, state="recovery", pending_operation="refine",
                                pending_payload="old", queued_feedback="later"))
        self.controller.handle(update("/cancel"))
        session = self.store.session(42)
        self.assertEqual((session.state, session.pending_operation, session.queued_feedback),
                         ("idle", "", ""))

    def test_reset_discards_draft_and_active_cv(self):
        self.store.save(Session(42, state="collecting_description", description="role",
                                active_job_folder="/jobs/acme", latest_pdf="/jobs/acme/cv.pdf",
                                session_active=1))
        self.controller.handle(update("/reset"))
        self.controller.handle(update("/status"))
        self.assertIn("State: idle. Active CV: no.", self.api.messages[-1][1])
        self.controller.handle(update("/resend"))
        session = self.store.session(42)
        self.assertEqual((session.state, session.description, session.session_active), ("idle", "", 0))
        self.assertEqual((session.active_job_folder, session.latest_pdf), ("", ""))
        self.assertIn("No generated PDF", self.api.messages[-1][1])

    def test_group_message_does_not_run_workflow(self):
        self.controller.handle(update("/new", chat_type="group"))
        self.assertTrue(self.work.empty())


if __name__ == "__main__":
    unittest.main()
