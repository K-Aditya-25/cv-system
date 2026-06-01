import sys
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.telegram_bot.resolver.browser import BrowserConfig, PlaywrightBrowserAdapter


class ResolverBrowserSecurityTests(unittest.TestCase):
    def test_browser_aborts_unsafe_subresource(self):
        page = MagicMock()
        page.goto.return_value = SimpleNamespace(url="https://jobs.example/42")
        browser = MagicMock(new_page=MagicMock(return_value=page))
        playwright = SimpleNamespace(chromium=MagicMock(launch=MagicMock(return_value=browser)))
        context, module = MagicMock(), ModuleType("playwright.sync_api")
        context.__enter__.return_value = playwright
        module.sync_playwright = lambda: context

        def goto(*_args, **_kwargs):
            route = MagicMock()
            route.request.url = "http://localhost/private"
            page.route.call_args.args[1](route)
            return SimpleNamespace(url="https://jobs.example/42")

        page.goto.side_effect = goto
        validate = lambda url: url if url.startswith("https://") else False
        with patch.dict(sys.modules, {"playwright.sync_api": module}):
            result = PlaywrightBrowserAdapter(BrowserConfig(enabled=True)).render(
                "https://jobs.example/42", validate_url=validate,
            )
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
