from __future__ import annotations

from typing import Any

from scripts.job_creation.env import get_env_secret

from .models import Session, WorkItem
from .resolver.browser import BrowserConfig, PlaywrightBrowserAdapter
from .resolver.discovery import DiscoveryService
from .resolver.service import ResolverService
from .resolver_models import ResolutionRequest, ResolutionResult


def resolve(item: WorkItem, api: Any = None) -> ResolutionResult:
    progress = lambda stage, _url: _progress(api, item.chat_id, stage)
    service = ResolverService(browser=_browser(), discover=_discover, progress=progress)
    return service.resolve(ResolutionRequest.from_json(item.payload))


def apply_result(runtime: Any, item: WorkItem, result: Any) -> None:
    session = runtime.store.session(item.chat_id)
    if not current(session, item):
        return
    if result.status == "resolved" and result.posting:
        session.description, session.state = result.posting.description, "collecting_instructions"
        session.pending_operation, session.pending_payload, session.last_error = "", "", ""
        runtime.store.save(session)
        runtime.api.send_message(item.chat_id, _success_message(result))
    elif result.status == "needs_explicit_link":
        _ask_for_careers(runtime, session, result.reason or "The job page needs a careers-page retry.")
    else:
        _fallback(runtime, session, result.reason or "No job description was found.")


def fail(runtime: Any, item: WorkItem, error: str) -> None:
    session = runtime.store.session(item.chat_id)
    if not current(session, item):
        return
    session.state, session.last_error = "recovery", error
    runtime.store.save(session)
    runtime.api.send_message(item.chat_id, f"URL resolution failed: {error}\nUse /done to retry or /cancel.")


def current(session: Session, item: WorkItem) -> bool:
    request_id = getattr(item, "request_id", session.request_id)
    return session.request_id == request_id and session.pending_operation == item.operation


def _progress(api: Any, chat_id: int, stage: str) -> None:
    if api and stage == "discover":
        api.send_message(chat_id, "The job page was unavailable. Searching careers pages.")


def _success_message(result: ResolutionResult) -> str:
    metadata = result.posting.metadata
    details = " - ".join(part for part in (metadata.company, metadata.role) if part)
    found = f"Job description found: {details}." if details else "Job description found."
    return f"{found}\nSend optional instructions, then /done. Use /none for defaults."


def _discover(query: str) -> tuple[str, ...]:
    return tuple(candidate.url for candidate in DiscoveryService().search(query).candidates)


def _browser() -> PlaywrightBrowserAdapter | None:
    enabled = (get_env_secret("TELEGRAM_RESOLVER_PLAYWRIGHT") or "").lower()
    if enabled in {"1", "true", "yes", "on"}:
        return PlaywrightBrowserAdapter(BrowserConfig(enabled=True))
    return None


def _ask_for_careers(runtime: Any, session: Session, reason: str) -> None:
    session.state, session.careers_url, session.last_error = "awaiting_careers_url", "", reason
    session.pending_operation, session.pending_payload = "", ""
    runtime.store.save(session)
    runtime.api.send_message(
        session.chat_id, f"{reason}\nSend the company's careers-page URL to retry, or paste the job description/send a .txt file.",
    )


def _fallback(runtime: Any, session: Session, reason: str) -> None:
    session.state, session.job_url, session.careers_url = "collecting_description", "", ""
    session.pending_operation, session.pending_payload, session.last_error = "", "", reason
    runtime.store.save(session)
    runtime.api.send_message(
        session.chat_id, f"{reason}\nPaste the job description, send it in chunks, or upload a .txt file. Use /done when finished.",
    )
