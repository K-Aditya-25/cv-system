from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from .job_section_markers import keeps_visible_text_block

BLOCK_TAGS = {"body", "article", "main", "section", "div", "p", "li", "ul", "ol", "h1", "h2", "h3"}
HIDDEN_TAGS = {"script", "style", "noscript", "template", "svg"}


@dataclass(frozen=True)
class VisibleBlock:
    index: int
    tag: str
    text: str
    link_chars: int

    @property
    def link_density(self) -> float:
        return self.link_chars / max(len(self.text), 1)


class JobPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.json_ld = False
        self.link_depth = 0
        self.scripts: list[str] = []
        self.links: list[str] = []
        self._stack: list[tuple[str, list[str], int]] = []
        self.blocks: list[VisibleBlock] = []

    def handle_starttag(self, tag, attrs) -> None:
        values = dict(attrs)
        if tag == "br" and not self.hidden and self._stack:
            self._stack[-1][1].append("\n")
        if tag in HIDDEN_TAGS:
            self.hidden += 1
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.json_ld = True
        if tag == "a":
            self.link_depth += 1
            if values.get("href"):
                self.links.append(values["href"])
        if not self.hidden and tag in BLOCK_TAGS:
            self._stack.append((tag, [], 0))

    def handle_endtag(self, tag) -> None:
        if tag == "script":
            self.json_ld = False
        if tag == "a" and self.link_depth:
            self.link_depth -= 1
        if not self.hidden and self._stack and self._stack[-1][0] == tag:
            self._finish_block()
        if tag in HIDDEN_TAGS and self.hidden:
            self.hidden -= 1

    def handle_startendtag(self, tag, attrs) -> None:
        if tag == "br" and not self.hidden and self._stack:
            self._stack[-1][1].append("\n")

    def handle_data(self, data) -> None:
        if self.json_ld:
            self.scripts.append(data)
        elif not self.hidden and self._stack:
            self._stack[-1][1].append(data)
            self._stack[-1] = (self._stack[-1][0], self._stack[-1][1],
                               self._stack[-1][2] + (len(data) if self.link_depth else 0))

    def _finish_block(self) -> None:
        tag, parts, link_chars = self._stack.pop()
        raw = " ".join(parts)
        split_tags = {"body", "article", "main", "section", "div"}
        segments = [raw]
        if tag in split_tags:
            segments = [item for item in re.split(r"\n+", raw) if item.strip()]
        if not segments:
            segments = [raw]
        for segment in segments:
            text = re.sub(r"\s+", " ", segment).strip()
            if keeps_visible_text_block(text):
                self._append_blocks(tag, text, link_chars)

    def _append_blocks(self, tag: str, text: str, link_chars: int) -> None:
        words = text.split()
        if len(words) <= 120:
            self.blocks.append(VisibleBlock(len(self.blocks), tag, text, link_chars))
            return
        for start in range(0, len(words), 60):
            chunk = " ".join(words[start:start + 60])
            self.blocks.append(VisibleBlock(len(self.blocks), tag, chunk, link_chars))
