import sqlite3
import tempfile
import unittest
from pathlib import Path

from scripts.telegram_bot.models import Session
from scripts.telegram_bot.store import StateStore


class StateStoreTests(unittest.TestCase):
    def test_session_values_persist_across_connections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.sqlite3"
            store = StateStore(path)
            store.save(Session(42, state="instructions", description="role", latest_pdf="cv.pdf"))
            reopened = StateStore(path)
            session = reopened.session(42)
        self.assertEqual(session.state, "instructions")
        self.assertEqual(session.description, "role")
        self.assertEqual(session.pdf_path, Path("cv.pdf"))

    def test_offset_persists_across_connections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.sqlite3"
            store = StateStore(path)
            self.assertIsNone(store.offset())
            store.set_offset(123)
            self.assertEqual(StateStore(path).offset(), 123)

    def test_recover_interrupted_marks_only_pending_busy_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(1, state="busy", pending_operation="generate"))
            store.save(Session(2, state="busy"))
            store.save(Session(3, state="idle", pending_operation="refine"))
            store.recover_interrupted()
            states = [store.session(chat_id).state for chat_id in (1, 2, 3)]
        self.assertEqual(states, ["recovery", "busy", "idle"])

    def test_reset_for_startup_discards_transient_work(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(1, state="busy", description="role", queued_feedback="change",
                               pending_operation="refine", session_active=1))
            store.reset_for_startup()
            session = store.session(1)
        self.assertEqual((session.state, session.description, session.queued_feedback), ("idle", "", ""))
        self.assertEqual((session.pending_operation, session.session_active), ("", 0))

    def test_existing_database_adds_url_resolver_columns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "state.sqlite3"
            connection = sqlite3.connect(path)
            connection.execute(
                "CREATE TABLE sessions (chat_id INTEGER PRIMARY KEY, state TEXT DEFAULT 'idle', "
                "description TEXT DEFAULT '', instructions TEXT DEFAULT '', "
                "active_job_folder TEXT DEFAULT '', latest_pdf TEXT DEFAULT '', "
                "queued_feedback TEXT DEFAULT '', pending_operation TEXT DEFAULT '', "
                "pending_payload TEXT DEFAULT '', last_error TEXT DEFAULT '', "
                "session_active INTEGER DEFAULT 0)"
            )
            connection.execute("INSERT INTO sessions(chat_id) VALUES (42)")
            connection.commit()
            connection.close()
            session = StateStore(path).session(42)
        self.assertEqual((session.job_url, session.careers_url, session.request_id), ("", "", 0))


if __name__ == "__main__":
    unittest.main()
