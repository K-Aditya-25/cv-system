from scripts.telegram_bot.models import Session
from tests.telegram_controller_fixtures import ControllerTestCase, update


class TelegramBusyCommandTests(ControllerTestCase):
    def test_busy_cv_work_cannot_be_cancelled_or_replaced(self):
        for command in ("/new", "/cancel", "/reset"):
            with self.subTest(command=command):
                self.store.save(Session(42, state="busy", pending_operation="create",
                                        session_active=1))
                self.controller.handle(update(command))
                self.assertEqual(self.store.session(42).state, "busy")
                self.assertIn("operation is running", self.api.messages[-1][1])


if __name__ == "__main__":
    import unittest
    unittest.main()
