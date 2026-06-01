from __future__ import annotations

from pathlib import Path

from scripts.job_creation.paths import ROOT

from .api import TelegramApi
from .controller_actions import clear
from .job_catalog import available_jobs, numbered_jobs
from .models import Session
from .store import StateStore


def begin_refine(api: TelegramApi, store: StateStore, session: Session) -> None:
    jobs = available_jobs(ROOT / "jobs")
    if not jobs:
        api.send_message(session.chat_id, "No generated CVs are available to refine.")
        return
    clear(session, "choosing_refine", active=1)
    store.save(session)
    api.send_message(session.chat_id, numbered_jobs(jobs))


def choose_refine(api: TelegramApi, store: StateStore, session: Session, text: str) -> None:
    jobs = available_jobs(ROOT / "jobs")
    if not text.isdigit() or not (1 <= int(text) <= len(jobs)):
        api.send_message(session.chat_id, "Reply with one of the listed CV numbers or use /cancel.")
        return
    job = jobs[int(text) - 1]
    session.active_job_folder, session.latest_pdf = str(job.folder), str(job.pdf)
    session.state = "idle"
    store.save(session)
    api.send_message(session.chat_id, f"Selected {job.label}. Send refinement feedback.")


def add_text_document(api: TelegramApi, store: StateStore, session: Session, document: dict) -> None:
    if session.state != "collecting_description" or Path(document.get("file_name", "")).suffix.lower() != ".txt":
        api.send_message(session.chat_id, "Send .txt files only while collecting a job description.")
        return
    try:
        downloaded = api.download_text(document["file_id"])
    except (RuntimeError, UnicodeDecodeError, ValueError) as error:
        api.send_message(session.chat_id, f"Could not read that .txt file: {error}")
        return
    session.description = "\n\n".join(
        part for part in (session.description.strip(), downloaded.strip()) if part
    )
    store.save(session)
    api.send_message(session.chat_id, "Job-description .txt file added. Send more text or use /done.")
