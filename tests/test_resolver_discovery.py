import json
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.telegram_bot.resolver.browser import BrowserConfig, PlaywrightBrowserAdapter
from scripts.telegram_bot.resolver.discovery import DiscoveryService
from scripts.telegram_bot.resolver.providers import (
    SearchCandidate, SearchOutcome,
)
from scripts.telegram_bot.resolver.extract import ExtractedJob
from scripts.telegram_bot.resolver.fetch import FetchError, FetchResult
from scripts.telegram_bot.resolver.service import ResolverService
from scripts.telegram_bot.resolver_models import ResolutionRequest

FIXTURES = Path(__file__).parent / "fixtures" / "resolver"


class JsonResponse:
    def __init__(self, name):
        self.body = (FIXTURES / name).read_bytes()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.body


class ResolverDiscoveryTests(unittest.TestCase):
    def test_tavily_empty_results_fall_back_to_brave(self):
        values = {"TAVILY_API_KEY": "t", "BRAVE_SEARCH_API_KEY": "b"}
        responses = [JsonResponse("tavily_empty.json"), JsonResponse("brave_results.json")]
        with patch("scripts.telegram_bot.resolver.providers.get_env_secret",
                   side_effect=lambda name: values.get(name)):
            with patch("urllib.request.urlopen", side_effect=responses):
                outcome = DiscoveryService().search("Acme platform engineer")
        self.assertEqual([item.provider for item in outcome.attempts], ["tavily", "brave"])
        self.assertEqual(outcome.candidates[0].url, "https://careers.acme.example/jobs/42")

    def test_provider_errors_continue_to_next_provider(self):
        first = MagicMock(search=MagicMock(return_value=SearchOutcome("tavily",
                                                                      unavailable_reason="offline")))
        second = MagicMock(search=MagicMock(return_value=SearchOutcome("brave")))
        outcome = DiscoveryService([first, second]).search("role")
        self.assertEqual(len(outcome.attempts), 2)

    def test_optional_browser_path_returns_rendered_html(self):
        page = MagicMock()
        page.goto.return_value = SimpleNamespace(url="https://jobs.example/42")
        page.content.return_value = "<html>rendered</html>"
        browser = MagicMock(new_page=MagicMock(return_value=page))
        playwright = SimpleNamespace(chromium=MagicMock(
            launch=MagicMock(return_value=browser)))
        context = MagicMock()
        context.__enter__.return_value = playwright
        module = ModuleType("playwright.sync_api")
        module.sync_playwright = lambda: context
        with patch.dict(sys.modules, {"playwright.sync_api": module}):
            result = PlaywrightBrowserAdapter(BrowserConfig(enabled=True)).render(
                "https://jobs.example/42", validate_url=lambda _url: True)
        self.assertEqual(result.html, "<html>rendered</html>")
        browser.close.assert_called_once()

    def test_service_fetches_discovered_candidate(self):
        candidate = SearchCandidate("https://careers.example/jobs/42", "Role", "", "brave")
        discover = MagicMock(search=MagicMock(return_value=SimpleNamespace(candidates=(candidate,))))
        fetch = MagicMock(side_effect=[FetchError("blocked"), FetchResult(candidate.url, "<html/>")])
        extract = MagicMock(return_value=ExtractedJob("description " * 40))
        result = ResolverService(fetch=fetch, extract=extract, discover=discover).resolve(
            ResolutionRequest(1, "https://linkedin.example/jobs/42"))
        self.assertEqual(result.status, "resolved")
        self.assertEqual(fetch.call_args_list[-1].args[0], candidate.url)


if __name__ == "__main__":
    unittest.main()
