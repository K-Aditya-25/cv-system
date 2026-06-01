import contextlib
import io
import unittest
from unittest.mock import patch

from scripts.run_telegram_bot import main


class RunTelegramBotTests(unittest.TestCase):
    def test_main_reports_configuration_error(self):
        stderr = io.StringIO()
        with patch("scripts.run_telegram_bot.load_config", side_effect=ValueError("missing token")):
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main(), 1)
        self.assertIn("Telegram bot configuration failed: missing token", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
