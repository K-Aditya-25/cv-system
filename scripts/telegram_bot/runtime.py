from __future__ import annotations

import json
import time
from pathlib import Path
from queue import Queue
from threading import Thread

from .api import TelegramApi
from .commands import COMMANDS
from .config import BotConfig
from .controller import BotController
from .controller_actions import start_queued_refinement
from .models import Session, WorkItem
from .runtime_url import apply_result, current, fail, resolve
from .store import StateStore
from .workflow import CvWorkflow
class BotRuntime:
    def __init__(self, config: BotConfig):
        self.api = TelegramApi(config.token)
        self.store = StateStore(config.database_path)
        self.workflow = CvWorkflow(config.master_data_path)
        self.work: Queue[WorkItem] = Queue()
        self.controller = BotController(self.api, self.store, self.work, config.allowed_chat_ids)
    def run(self) -> None:
        identity = self.api.get_me()
        self.api.delete_webhook(drop_pending_updates=True)
        self.api.set_commands(COMMANDS)
        self.store.reset_for_startup()
        print(f"Telegram CV bot @{identity['username']} is polling for messages.", flush=True)
        print("Press Ctrl-C to stop.", flush=True)
        Thread(target=self._worker, daemon=True).start()
        while True:
            try:
                self._poll()
            except Exception as error:
                print(f"Telegram polling failed: {error}", flush=True)
                time.sleep(3)
    def _poll(self) -> None:
        for update in self.api.updates(self.store.offset()):
            self.controller.handle(update)
            self.store.set_offset(update["update_id"] + 1)
    def _worker(self) -> None:
        while True:
            item = self.work.get()
            try:
                self._execute(item)
            finally:
                self.work.task_done()
    def _execute(self, item: WorkItem) -> None:
        try:
            session = self.store.session(item.chat_id)
            if not current(session, item):
                return
            if item.operation == "resolve_url":
                apply_result(self, item, resolve(item, self.api))
                return
            if item.operation == "create":
                payload = json.loads(item.payload)
                model_key = str(payload.get("model_key") or session.model_key or "")
                folder, pdf = self.workflow.create(payload["description"], payload["instructions"], model_key)
                if not current(self.store.session(item.chat_id), item):
                    return
                session.active_job_folder = str(folder)
                session.model_key = model_key
                self.store.save(session)
            elif item.operation == "refine":
                pdf = self.workflow.refine(Path(session.active_job_folder), item.payload, session.model_key)
            else:
                raise ValueError(f"Unknown work operation: {item.operation}")
            self._complete_item(item, pdf)
        except Exception as error:
            session = self.store.session(item.chat_id)
            if item.operation == "resolve_url":
                fail(self, item, str(error))
                return
            if not current(session, item):
                return
            session.state, session.last_error = "recovery", str(error)
            self.store.save(session)
            self.api.send_message(item.chat_id, f"CV operation failed: {error}\nUse /done to retry or /cancel.")
    def _complete_item(self, item: WorkItem, pdf: Path) -> None:
        if current(self.store.session(item.chat_id), item):
            self._complete(item.chat_id, pdf)
    def _complete(self, chat_id: int, pdf: Path) -> None:
        session = self.store.session(chat_id)
        session.latest_pdf, session.last_error = str(pdf), ""
        session.pending_operation, session.pending_payload = "", ""
        session.state = "idle"
        self.store.save(session)
        try:
            self.api.send_document(chat_id, pdf)
        except Exception as error:
            self.api.send_message(chat_id, f"PDF delivery failed: {error}\nUse /resend to try again.")
        start_queued_refinement(self.api, self.store, self.work, self.store.session(chat_id))
