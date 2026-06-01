import socket
import unittest

from scripts.telegram_bot.resolver.input import https_url_only
from scripts.telegram_bot.resolver.security import UnsafeUrlError, validate_public_https_url


def addresses(*values):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (value, 443)) for value in values]


class ResolverUrlPolicyTests(unittest.TestCase):
    def test_intake_accepts_only_one_https_url(self):
        self.assertEqual(https_url_only(" https://jobs.example/42 "), "https://jobs.example/42")
        for value in ("http://jobs.example/42", "https://jobs.example/42 extra", "hello"):
            self.assertIsNone(https_url_only(value))

    def test_ssrf_rejects_private_and_mixed_dns_results(self):
        for values in (("127.0.0.1",), ("93.184.216.34", "10.0.0.1")):
            with self.assertRaisesRegex(UnsafeUrlError, "public IP"):
                validate_public_https_url("https://jobs.example/42",
                                          resolver=lambda *_args, **_kwargs: addresses(*values))

    def test_ssrf_rejects_credentials_and_localhost(self):
        for url in ("https://user:pass@jobs.example/42", "https://localhost/42"):
            with self.assertRaises(UnsafeUrlError):
                validate_public_https_url(url)

    def test_public_url_is_normalized_without_fragment(self):
        result = validate_public_https_url(
            "HTTPS://JOBS.EXAMPLE/path?q=1#section",
            resolver=lambda *_args, **_kwargs: addresses("93.184.216.34"),
        )
        self.assertEqual(result, "https://jobs.example/path?q=1")


if __name__ == "__main__":
    unittest.main()
