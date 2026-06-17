from __future__ import annotations

import json
from queue import Queue

from scripts.job_creation.model_catalog import model_menu_text, resolve_model_choice
from scripts.job_creation.model_logging import log_event

from .api import TelegramApi
from .controller_actions import save, start
from .models import Session, WorkItem
from .store import StateStore


def choose_model(api: TelegramApi, store: StateStore, session: Session, text: str) -> None:
    route = resolve_model_choice(text)
    if route is None:
        api.send_message(session.chat_id, model_menu_text())
        return
    session.model_key = route.key
    session.state = "collecting_instructions"
    log_event(
        "model.select", chat_id=session.chat_id, model_key=route.key,
        provider=route.provider, model=route.model, label=route.label,
    )
    save(
        api,
        store,
        session,
        f"Using {route.label}. Send optional instructions in chunks, then /done. Use /none for defaults.",
    )


def start_create(
    api: TelegramApi,
    store: StateStore,
    work: Queue[WorkItem],
    session: Session,
    instructions: str,
) -> None:
    payload = json.dumps({
        "description": session.description,
        "instructions": instructions,
        "model_key": session.model_key,
    })
    log_event(
        "model.operation", operation="create_queued", chat_id=session.chat_id,
        model_key=session.model_key, description_chars=len(session.description),
        instructions_chars=len(instructions),
    )
    start(api, store, work, session, "create", payload, "Generating CV.")
