from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterable

from .html_text import html_to_text


@dataclass(frozen=True)
class StructuredJob:
    description: str
    title: str = ""
    company: str = ""
    location: str = ""


def job_from_json_ld(scripts: Iterable[str]) -> StructuredJob | None:
    for script in scripts:
        try:
            job = next(_jobs(json.loads(script)))
        except (json.JSONDecodeError, StopIteration):
            continue
        organization = job.get("hiringOrganization") or {}
        location = job.get("jobLocation") or {}
        address = location.get("address", {}) if isinstance(location, dict) else {}
        return StructuredJob(
            html_to_text(str(job.get("description", ""))),
            str(job.get("title", "")),
            str(organization.get("name", "")),
            str(address.get("addressLocality", "")),
        )
    return None


def _jobs(value: Any):
    if isinstance(value, dict):
        types = value.get("@type", [])
        type_values = types if isinstance(types, list) else [types]
        if "JobPosting" in type_values:
            yield value
        for child in value.values():
            yield from _jobs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _jobs(child)
