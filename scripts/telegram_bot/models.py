from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Session:
    chat_id: int
    state: str = "idle"
    description: str = ""
    instructions: str = ""
    active_job_folder: str = ""
    latest_pdf: str = ""
    queued_feedback: str = ""
    pending_operation: str = ""
    pending_payload: str = ""
    last_error: str = ""
    session_active: int = 0
    job_url: str = ""
    careers_url: str = ""
    request_id: int = 0

    @property
    def pdf_path(self) -> Path | None:
        return Path(self.latest_pdf) if self.latest_pdf else None


@dataclass(frozen=True)
class WorkItem:
    chat_id: int
    operation: str
    payload: str
    request_id: int = 0
