import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.telegram_bot.api import TelegramApi
from scripts.telegram_bot.multipart import document_body
from tests.telegram_fixtures import FakeResponse


class TelegramApiTests(unittest.TestCase):
    def test_send_message_chunks_text(self) -> None:
        api = TelegramApi("token")
        with patch.object(api, "_json") as request:
            api.send_message(42, "a" * 4001)
        self.assertEqual(request.call_count, 2)
        self.assertEqual(request.call_args_list[0].args, ("sendMessage", {"chat_id": 42, "text": "a" * 4000}))
        self.assertEqual(request.call_args_list[1].args, ("sendMessage", {"chat_id": 42, "text": "a"}))

    def test_updates_sends_offset_when_present(self) -> None:
        api = TelegramApi("token")
        with patch.object(api, "_json", return_value=[]) as request:
            self.assertEqual(api.updates(9), [])
        self.assertEqual(request.call_args.args[1]["offset"], 9)

    def test_set_commands_posts_command_menu(self) -> None:
        api = TelegramApi("token")
        commands = [{"command": "whoami", "description": "Show chat ID"}]
        with patch.object(api, "_json") as request:
            api.set_commands(commands)
        request.assert_called_once_with("setMyCommands", {"commands": commands})

    def test_delete_webhook_can_drop_offline_updates(self) -> None:
        api = TelegramApi("token")
        with patch.object(api, "_json") as request:
            api.delete_webhook(drop_pending_updates=True)
        request.assert_called_once_with("deleteWebhook", {"drop_pending_updates": True})

    def test_json_returns_result_and_raises_for_api_error(self) -> None:
        api = TelegramApi("token")
        with patch("urllib.request.urlopen", return_value=FakeResponse({"ok": True, "result": {"id": 1}})):
            self.assertEqual(api.get_me(), {"id": 1})
        with patch("urllib.request.urlopen", return_value=FakeResponse({"ok": False, "description": "bad"})):
            with self.assertRaisesRegex(RuntimeError, "bad"):
                api.get_me()

    def test_document_body_contains_pdf_and_chat_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cv.pdf"
            path.write_bytes(b"%PDF")
            body, content_type = document_body(42, path)
        self.assertIn(b'name="chat_id"\r\n\r\n42', body)
        self.assertIn(b'filename="cv.pdf"', body)
        self.assertIn(b"Content-Type: application/pdf", body)
        self.assertIn(b"%PDF", body)
        self.assertIn("multipart/form-data; boundary=", content_type)

    def test_send_document_posts_multipart_body(self) -> None:
        api = TelegramApi("token")
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "cv.pdf"
            path.write_bytes(b"%PDF")
            with patch("urllib.request.urlopen", return_value=FakeResponse({"ok": True, "result": {}})) as urlopen:
                api.send_document(42, path)
        request = urlopen.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/sendDocument"))
        self.assertIn(b'filename="cv.pdf"', request.data)
        self.assertIn(b"%PDF", request.data)
        self.assertTrue(request.headers["Content-type"].startswith("multipart/form-data; boundary="))

    def test_download_text_fetches_file_contents(self) -> None:
        api = TelegramApi("token")
        with patch.object(api, "_json", return_value={"file_path": "jobs/role.txt"}):
            with patch("urllib.request.urlopen", return_value=FakeResponse(b"job description")):
                self.assertEqual(api.download_text("file-id"), "job description")

    def test_download_text_rejects_files_over_250_kb(self) -> None:
        api = TelegramApi("token")
        with patch.object(api, "_json", return_value={"file_path": "jobs/role.txt"}):
            with patch("urllib.request.urlopen", return_value=FakeResponse(b"x" * 250_001)):
                with self.assertRaisesRegex(ValueError, "250 KB"):
                    api.download_text("file-id")


if __name__ == "__main__":
    unittest.main()
