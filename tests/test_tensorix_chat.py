import http.client
import json
import unittest
from unittest.mock import MagicMock, patch

from scripts.job_creation.errors import IntakeError
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

    def test_tensorix_chat_accepts_typed_content_parts(self):
        response = {"choices": [{"message": {"content": [{"type": "text", "text": "hello"}]}}]}
        with patch("scripts.job_creation.tensorix_chat.get_env_secret", return_value="secret"):
            with patch("urllib.request.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
                self.assertEqual(tensorix_chat("system", "user"), "hello")

    def test_tensorix_chat_empty_message_error_includes_response_shape(self):
        response = {
            "choices": [{
                "finish_reason": "length",
                "message": {"role": "assistant", "content": "", "reasoning_content": "thinking"},
            }],
        }
        with patch("scripts.job_creation.tensorix_chat.get_env_secret", return_value="secret"):
            with patch("urllib.request.urlopen") as urlopen:
                urlopen.return_value.__enter__.return_value.read.return_value = json.dumps(response).encode()
                with self.assertRaisesRegex(IntakeError, "finish_reason=length"):
                    tensorix_chat("system", "user", purpose="Tensorix CV model")

    def test_tensorix_chat_retries_remote_disconnect_when_requested(self):
        response = {"choices": [{"message": {"content": "ok"}}]}
        successful = MagicMock()
        successful.__enter__.return_value.read.return_value = json.dumps(response).encode()
        with patch("scripts.job_creation.tensorix_chat.get_env_secret", return_value="secret"):
            with patch("scripts.job_creation.tensorix_chat.time.sleep"):
                with patch("urllib.request.urlopen") as urlopen:
                    urlopen.side_effect = [http.client.RemoteDisconnected(), successful]
                    text = tensorix_chat("system", "user", attempts=2)
        self.assertEqual(text, "ok")
        self.assertEqual(urlopen.call_count, 2)


if __name__ == "__main__":
    unittest.main()
