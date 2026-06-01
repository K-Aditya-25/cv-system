from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any, Literal

ResolutionStatus = Literal["resolved", "needs_explicit_link", "fallback_text"]
ResolutionMode = Literal["automatic", "explicit"]


@dataclass(frozen=True)
class JobMetadata:
    company: str = ""
    role: str = ""
    location: str = ""

    @classmethod
    def from_dict(cls, value: dict[str, Any] | None) -> JobMetadata:
        return cls(**(value or {}))


@dataclass(frozen=True)
class FetchedPage:
    requested_url: str
    final_url: str
    content_type: str
    body: bytes


@dataclass(frozen=True)
class ExtractedPosting:
    description: str
    metadata: JobMetadata
    canonical_url: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ExtractedPosting:
        return cls(value["description"], JobMetadata.from_dict(value.get("metadata")), value["canonical_url"])


@dataclass(frozen=True)
class ResolutionRequest:
    request_id: int
    url: str
    mode: ResolutionMode = "automatic"
    inferred: JobMetadata | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> ResolutionRequest:
        data = json.loads(value)
        data["inferred"] = JobMetadata.from_dict(data.get("inferred")) if data.get("inferred") else None
        return cls(**data)


@dataclass(frozen=True)
class ResolutionResult:
    status: ResolutionStatus
    posting: ExtractedPosting | None = None
    metadata: JobMetadata | None = None
    reason: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_json(cls, value: str) -> ResolutionResult:
        data = json.loads(value)
        data["posting"] = ExtractedPosting.from_dict(data["posting"]) if data.get("posting") else None
        data["metadata"] = JobMetadata.from_dict(data["metadata"]) if data.get("metadata") else None
        return cls(**data)


@dataclass(frozen=True)
class SearchCandidate:
    url: str
    title: str = ""
    snippet: str = ""
    provider: str = ""
    provider_score: float | None = None
