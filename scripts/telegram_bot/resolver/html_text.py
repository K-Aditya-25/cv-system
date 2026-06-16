from __future__ import annotations

import html
import re
from html.parser import HTMLParser

BREAK_TAGS = {"br", "p", "div", "li", "ul", "ol", "h1", "h2", "h3"}


class _TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in BREAK_TAGS:
            self._break()

    def handle_endtag(self, tag: str) -> None:
        if tag in BREAK_TAGS:
            self._break()

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)

    def _break(self) -> None:
        if self.parts and self.parts[-1] != "\n":
            self.parts.append("\n")


def html_to_text(value: str) -> str:
    parser = _TextParser()
    parser.feed(html.unescape(value))
    text = "".join(parser.parts)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()
