import json
import unittest
from unittest.mock import patch

from scripts.job_creation.tensorix_chat import tensorix_chat


class TensorixChatTests(unittest.TestCase):
    def test_tensorix_key_uses_secret_loader(self):
        response = {"choices": [{"message": {"content": '{"route":"full_context_refinement"}'}}]}
        with patch("scripts.job_creation.tensorix_chat.get_env_secret", return_value="secret"):
            with patch("urllib.request.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
                text = tensorix_chat("system", "user", model="minimax/test", max_tokens=1234)
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode())
        self.assertEqual(text, '{"route":"full_context_refinement"}')
        self.assertEqual(payload["model"], "minimax/test")
        self.assertEqual(payload["max_tokens"], 1234)
        self.assertEqual(request.get_header("Authorization"), "Bearer secret")


if __name__ == "__main__":
    unittest.main()
