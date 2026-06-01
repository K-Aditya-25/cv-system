from __future__ import annotations

from queue import Queue

from .api import TelegramApi
from .controller_actions import append, start
from .models import Session, WorkItem
from .resolver.input import https_url_only
from .resolver_models import ResolutionRequest
from .store import StateStore


def route_url_text(api: TelegramApi, store: StateStore, work: Queue[WorkItem],
                   session: Session, text: str) -> bool:
    url = https_url_only(text)
    if session.state == "collecting_description" and not session.description and url:
        session.job_url = url
        _queue(api, store, work, session, "Checking the job posting URL.")
        return True
    if session.state != "awaiting_careers_url":
        return False
    if url:
        session.careers_url = url
        _queue(api, store, work, session, "Trying the careers-page URL.")
    else:
        session.description = append(session.description, text)
        session.state, session.job_url, session.careers_url = "collecting_description", "", ""
        store.save(session)
        api.send_message(session.chat_id, "Pasted job description added. Send more text or use /done.")
    return True


def _queue(api: TelegramApi, store: StateStore, work: Queue[WorkItem],
           session: Session, notice: str) -> None:
    request_id = session.request_id + 1
    mode, url = ("explicit", session.careers_url) if session.careers_url else ("automatic", session.job_url)
    payload = ResolutionRequest(request_id, url, mode).to_json()
    start(api, store, work, session, "resolve_url", payload, notice, "resolving_job_url", request_id)


def status_text(session: Session) -> str:
    if session.state == "idle":
        return f"State: idle. Active CV: {'yes' if session.latest_pdf else 'no'}."
    details = {
        "collecting_description": "Collecting a job description. Send text, a .txt file, or one URL.",
        "resolving_job_url": "Checking the job posting URL in the background.",
        "awaiting_careers_url": "Waiting for a careers-page URL retry, pasted text, or a .txt file.",
        "collecting_instructions": "Job description is ready. Send optional instructions or /none.",
        "busy": "Generating or refining a CV in the background.",
        "recovery": "The last CV operation failed. Use /done to retry or /cancel.",
        "choosing_refine": "Waiting for a CV number to refine.",
    }
    return f"{details.get(session.state, f'State: {session.state}.')} Active CV: {'yes' if session.latest_pdf else 'no'}."
