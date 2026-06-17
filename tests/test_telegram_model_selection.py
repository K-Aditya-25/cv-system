import tempfile
import unittest
from pathlib import Path
from queue import Queue

from scripts.telegram_bot.models import Session
from scripts.telegram_bot.runtime import BotRuntime
from scripts.telegram_bot.store import StateStore
from tests.telegram_controller_fixtures import ControllerTestCase, update
from tests.test_telegram_runtime import RuntimeApi


class TelegramModelSelectionTests(ControllerTestCase):
    def test_description_done_asks_for_model_before_instructions(self):
        for text in ("/new", "Full job description", "/done"):
            self.controller.handle(update(text))
        session = self.store.session(42)
        self.assertEqual(session.state, "choosing_model")
        self.assertIn("Choose the model", self.api.messages[-1][1])
        self.controller.handle(update("not a model"))
        session = self.store.session(42)
        self.assertEqual(session.state, "choosing_model")
        self.assertIn("Reply with 1, 2, or 3", self.api.messages[-1][1])
        self.controller.handle(update("kimi"))
        session = self.store.session(42)
        self.assertEqual((session.state, session.model_key), ("collecting_instructions", "kimi"))


class TelegramRuntimeModelSelectionTests(unittest.TestCase):
    def test_create_passes_selected_model_key_to_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder, pdf = Path(temp_dir) / "job", Path(temp_dir) / "job" / "cv.pdf"
            calls = []
            store = StateStore(Path(temp_dir) / "state.sqlite3")
            store.save(Session(42, state="busy", pending_operation="create", model_key="glm"))
            runtime = object.__new__(BotRuntime)
            runtime.store, runtime.api, runtime.work = store, RuntimeApi(), Queue()

            def create(_self, _description, _instructions, model_key):
                calls.append(model_key)
                return folder, pdf

            runtime.workflow = type("Workflow", (), {"create": create})()
            runtime._execute(type("Item", (), {
                "chat_id": 42, "operation": "create",
                "payload": '{"description": "role", "instructions": "none", "model_key": "glm"}',
            })())
            self.assertEqual(calls, ["glm"])
            self.assertEqual(store.session(42).model_key, "glm")


if __name__ == "__main__":
    unittest.main()
