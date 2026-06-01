import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.telegram_bot.config import load_config


class TelegramConfigTests(unittest.TestCase):
    def test_load_config_requires_explicit_master_data(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "CV_MASTER_DATA"):
                load_config()

    def test_load_config_reads_allowed_ids_and_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            master = Path(temp_dir) / "master.yaml"
            master.write_text("profile: {}", encoding="utf-8")
            env = {
                "CV_MASTER_DATA": str(master),
                "TELEGRAM_ALLOWED_CHAT_IDS": "42, 43",
                "TELEGRAM_BOT_TOKEN": "token",
                "TELEGRAM_STATE_DB": str(Path(temp_dir) / "state.sqlite3"),
            }
            with patch.dict(os.environ, env, clear=True):
                config = load_config()
        self.assertEqual(config.token, "token")
        self.assertEqual(config.allowed_chat_ids, {42, 43})
        self.assertEqual(config.master_data_path, master)

    def test_load_config_rejects_missing_master_data_file(self) -> None:
        env = {"CV_MASTER_DATA": "/missing/master.yaml"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaisesRegex(ValueError, "does not exist"):
                load_config()


if __name__ == "__main__":
    unittest.main()
