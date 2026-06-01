import tempfile
import unittest
from pathlib import Path
from queue import Queue

from scripts.telegram_bot.controller import BotController
from scripts.telegram_bot.store import StateStore


class FakeApi:
    def __init__(self):
        self.messages, self.documents = [], []

    def send_message(self, chat_id, text):
        self.messages.append((chat_id, text))

    def send_document(self, chat_id, path):
        self.documents.append((chat_id, path))

    def download_text(self, file_id):
        return f"downloaded {file_id}"


def update(text="", *, chat_id=42, chat_type="private", document=None):
    message = {"chat": {"id": chat_id, "type": chat_type}, "text": text}
    if document:
        message["document"] = document
    return {"message": message}


class ControllerTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = StateStore(Path(self.temp_dir.name) / "state.sqlite3")
        self.api, self.work = FakeApi(), Queue()
        self.controller = BotController(self.api, self.store, self.work, {42})

    def tearDown(self):
        self.temp_dir.cleanup()
