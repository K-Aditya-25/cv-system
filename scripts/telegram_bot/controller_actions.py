from __future__ import annotations

from queue import Queue

from .api import TelegramApi
from .models import Session, WorkItem
from .store import StateStore

HELP = (
    "/new - start a CV\n/refine - choose an existing CV\n/done - finish input\n"
    "/none - default instructions\n/cancel - clear draft\n"
    "/reset - clear session and active CV\n/status - show state\n"
    "/resend - send latest PDF\n/whoami - show this chat ID"
)


def append(existing: str, addition: str) -> str:
    return "\n\n".join(part for part in (existing.strip(), addition.strip()) if part)


def save(api: TelegramApi, store: StateStore, session: Session, notice: str) -> None:
    store.save(session)
    api.send_message(session.chat_id, notice)


def clear(session: Session, state: str = "idle", active: int = 0) -> None:
    session.state, session.description, session.instructions = state, "", ""
    session.queued_feedback, session.pending_operation, session.pending_payload = "", "", ""
    session.last_error, session.job_url, session.careers_url = "", "", ""
    session.request_id += 1
    session.session_active = active


def hard_reset(session: Session) -> None:
    clear(session)
    session.active_job_folder, session.latest_pdf = "", ""


def start(api: TelegramApi, store: StateStore, work: Queue[WorkItem], session: Session,
          operation: str, payload: str, notice: str, state: str = "busy",
          request_id: int | None = None) -> None:
    session.request_id = request_id if request_id is not None else session.request_id + 1
    session.state, session.pending_operation, session.pending_payload = state, operation, payload
    store.save(session)
    work.put(WorkItem(session.chat_id, operation, payload, session.request_id))
    api.send_message(session.chat_id, notice)


def resend(api: TelegramApi, session: Session) -> None:
    if session.pdf_path and session.pdf_path.exists():
        api.send_document(session.chat_id, session.pdf_path)
    else:
        api.send_message(session.chat_id, "No generated PDF is available yet.")


def start_queued_refinement(api: TelegramApi, store: StateStore, work: Queue[WorkItem],
                            session: Session) -> None:
    feedback = session.queued_feedback.strip()
    if not feedback:
        return
    session.queued_feedback = ""
    start(api, store, work, session, "refine", feedback, "Applying queued refinement feedback.")


def retry_pending(api: TelegramApi, store: StateStore, work: Queue[WorkItem],
                  session: Session) -> None:
    session.state = "resolving_job_url" if session.pending_operation == "resolve_url" else "busy"
    store.save(session)
    work.put(WorkItem(session.chat_id, session.pending_operation,
                      session.pending_payload, session.request_id))
    api.send_message(session.chat_id, "Retrying retained work.")
