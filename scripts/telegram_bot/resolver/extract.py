from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin
from scripts.telegram_bot.resolver_models import ExtractedPosting, FetchedPage, JobMetadata

class ExtractionError(ValueError):
    pass
@dataclass(frozen=True)
class ExtractedJob:
    description: str
    title: str = ""
    company: str = ""
    location: str = ""
    method: str = "html"

class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.json_ld = False
        self.scripts: list[str] = []
        self.text: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag, attrs) -> None:
        values = dict(attrs)
        if tag in {"script", "style", "noscript", "template"}:
            self.hidden += 1
        if tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self.json_ld = True
        if tag == "a" and values.get("href"):
            self.links.append(values["href"])

    def handle_endtag(self, tag) -> None:
        if tag == "script":
            self.json_ld = False
        if tag in {"script", "style", "noscript", "template"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data) -> None:
        if self.json_ld:
            self.scripts.append(data)
        elif not self.hidden:
            self.text.append(data)

def _clean(value: str) -> str:
    parser = _PageParser()
    parser.feed(value)
    return re.sub(r"\s+", " ", " ".join(parser.text)).strip()

def _jobs(value):
    if isinstance(value, dict):
        if value.get("@type") == "JobPosting" or "JobPosting" in value.get("@type", []):
            yield value
        for child in value.values():
            yield from _jobs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _jobs(child)

def _json_job(parser: _PageParser) -> ExtractedJob | None:
    for script in parser.scripts:
        try:
            job = next(_jobs(json.loads(script)))
        except (json.JSONDecodeError, StopIteration):
            continue
        organization = job.get("hiringOrganization") or {}
        location = job.get("jobLocation") or {}
        address = location.get("address", {}) if isinstance(location, dict) else {}
        return ExtractedJob(_clean(str(job.get("description", ""))), str(job.get("title", "")),
                            str(organization.get("name", "")), str(address.get("addressLocality", "")),
                            "json-ld")
    return None

def extract_job(html: str) -> ExtractedJob:
    parser = _PageParser()
    parser.feed(html)
    job = _json_job(parser) or ExtractedJob(re.sub(r"\s+", " ", " ".join(parser.text)).strip())
    lowered = job.description.lower()
    blocked = ("captcha", "verify you are human", "sign in to continue", "log in to continue")
    if len(job.description.split()) < 40 or any(marker in lowered for marker in blocked):
        raise ExtractionError("page does not contain a usable visible job description")
    return job

def extract_page(page: FetchedPage) -> ExtractedPosting:
    charset = "utf-8"
    if "charset=" in page.content_type.lower():
        charset = page.content_type.lower().split("charset=", 1)[1].split(";", 1)[0].strip()
    job = extract_job(page.body.decode(charset, errors="replace"))
    metadata = JobMetadata(company=job.company, role=job.title, location=job.location)
    return ExtractedPosting(job.description, metadata, page.final_url)

def listing_urls(html: str, base_url: str) -> list[str]:
    parser = _PageParser()
    parser.feed(html)
    return [urljoin(base_url, href) for href in parser.links]
