import tempfile
import unittest
from pathlib import Path
from queue import Queue

from scripts.telegram_bot.models import Session
from scripts.telegram_bot.runtime import BotRuntime
from scripts.telegram_bot.store import StateStore


class RuntimeApi:
    def __init__(self, store=None, fail=False):
        self.store, self.fail, self.messages = store, fail, []

    def send_document(self, chat_id, _path):
        if self.fail:
            raise RuntimeError("upload failed")
        if self.store:
            session = self.store.session(chat_id)
            session.queued_feedback = "arrived during upload"
            self.store.save(session)

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))


class StartupApi:
    def __init__(self):
        self.dropped = None

    def get_me(self):
        return {"username": "test_bot"}

    def delete_webhook(self, *, drop_pending_updates=False):
        self.dropped = drop_pending_updates

    def set_commands(self, _commands):
        return None

    def updates(self, _offset):
        raise KeyboardInterrupt


class TelegramRuntimeTests(unittest.TestCase):
    def runtime(self, store, api):
        runtime = object.__new__(BotRuntime)
        runtime.store, runtime.api, runtime.work = store, api, Queue()
        return runtime

    def test_delivery_failure_keeps_completed_pdf_for_resend(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(42, state="busy", pending_operation="create"))
            runtime = self.runtime(store, RuntimeApi(fail=True))
            runtime._complete(42, Path(temp_dir) / "cv.pdf")
            session = store.session(42)
        self.assertEqual(session.state, "idle")
        self.assertTrue(session.latest_pdf.endswith("cv.pdf"))
        self.assertIn("/resend", runtime.api.messages[-1][1])

    def test_feedback_arriving_during_upload_is_refined(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(42, state="busy", pending_operation="create"))
            runtime = self.runtime(store, RuntimeApi(store=store))
            runtime._complete(42, Path(temp_dir) / "cv.pdf")
            item = runtime.work.get_nowait()
        self.assertEqual(item.operation, "refine")
        self.assertEqual(item.payload, "arrived during upload")

    def test_create_saves_active_job_folder_before_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder, pdf = Path(temp_dir) / "job", Path(temp_dir) / "job" / "cv.pdf"
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(42, state="busy", pending_operation="create"))
            runtime = self.runtime(store, RuntimeApi())
            runtime.workflow = type("Workflow", (), {"create": lambda *_args: (folder, pdf)})()
            runtime._execute(type("Item", (), {
                "chat_id": 42, "operation": "create",
                "payload": '{"description": "role", "instructions": "none"}',
            })())
            self.assertEqual(store.session(42).active_job_folder, str(folder))

    def test_run_drops_offline_updates_and_resets_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(42, state="busy", queued_feedback="old", session_active=1))
            runtime, api = self.runtime(store, StartupApi()), StartupApi()
            runtime.api = api
            with self.assertRaises(KeyboardInterrupt):
                runtime.run()
            session = store.session(42)
        self.assertTrue(api.dropped)
        self.assertEqual((session.state, session.queued_feedback, session.session_active),
                         ("idle", "", 0))


if __name__ == "__main__":
    unittest.main()
