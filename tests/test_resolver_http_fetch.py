import unittest
from email.message import Message
from urllib.error import HTTPError

from scripts.telegram_bot.resolver.fetch import FetchError, fetch_html


class Response:
    def __init__(self, body=b"<html>ok</html>", url="https://jobs.example/42", content_type="text/html"):
        self.body, self.url, self.headers = body, url, Message()
        self.headers["Content-Type"] = content_type

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def geturl(self):
        return self.url

    def read(self, size=-1):
        return self.body[:size]


class Opener:
    def __init__(self, *results):
        self.results, self.requests = list(results), []

    def open(self, request, timeout):
        self.requests.append((request.full_url, timeout))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def validate(url):
    return url


class ResolverHttpFetchTests(unittest.TestCase):
    def test_fetch_caps_body_read(self):
        with self.assertRaisesRegex(FetchError, "byte limit"):
            fetch_html("https://jobs.example/42", max_bytes=4, validate=validate,
                       opener=Opener(Response(b"12345")))

    def test_fetch_rejects_non_html(self):
        with self.assertRaisesRegex(FetchError, "unsupported content"):
            fetch_html("https://jobs.example/42", validate=validate,
                       opener=Opener(Response(content_type="application/json")))

    def test_redirect_target_is_validated(self):
        headers = Message()
        headers["Location"] = "https://internal.example/admin"
        redirect = HTTPError("https://jobs.example/42", 302, "redirect", headers, None)
        seen = []
        fetch_html("https://jobs.example/42", validate=lambda url: seen.append(url) or url,
                   opener=Opener(redirect, Response()))
        self.assertEqual(seen, ["https://jobs.example/42", "https://internal.example/admin",
                                "https://jobs.example/42"])


if __name__ == "__main__":
    unittest.main()
