from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


UrlValidator = Callable[[str], object]


@dataclass(frozen=True)
class BrowserConfig:
    enabled: bool = False
    timeout_ms: int = 15_000


@dataclass(frozen=True)
class RenderedPage:
    url: str
    html: str


class BrowserAdapter(Protocol):
    def render(self, url: str, *, validate_url: UrlValidator) -> RenderedPage | None: ...


class PlaywrightBrowserAdapter:
    def __init__(self, config: BrowserConfig | None = None):
        self.config = config or BrowserConfig()

    def render(self, url: str, *, validate_url: UrlValidator) -> RenderedPage | None:
        if not self.config.enabled or validate_url(url) is False:
            return None
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return None
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    page = browser.new_page()
                    blocked = [False]

                    def intercept(route) -> None:
                        try:
                            allowed = validate_url(route.request.url) is not False
                        except Exception:
                            allowed = False
                        if not allowed:
                            blocked[0] = True
                            route.abort()
                            return
                        route.continue_()

                    page.route("**/*", intercept)
                    response = page.goto(url, wait_until="domcontentloaded",
                                         timeout=self.config.timeout_ms)
                    if blocked[0]:
                        return None
                    final_url = response.url if response else page.url
                    if validate_url(final_url) is False:
                        return None
                    return RenderedPage(final_url, page.content())
                finally:
                    browser.close()
        except Exception:
            return None
