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
from .models import Session, WorkItem
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
            if item.operation == "create":
                payload = json.loads(item.payload)
                folder, pdf = self.workflow.create(payload["description"], payload["instructions"])
                session.active_job_folder = str(folder)
                self.store.save(session)
            else:
                pdf = self.workflow.refine(Path(session.active_job_folder), item.payload)
            self._complete(item.chat_id, pdf)
        except Exception as error:
            session = self.store.session(item.chat_id)
            session.state, session.last_error = "recovery", str(error)
            self.store.save(session)
            self.api.send_message(item.chat_id, f"CV operation failed: {error}\nUse /done to retry or /cancel.")

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
        self._start_queued_refinement(self.store.session(chat_id))

    def _start_queued_refinement(self, session: Session) -> None:
        feedback = session.queued_feedback.strip()
        if not feedback:
            return
        session.queued_feedback = ""
        session.state, session.pending_operation, session.pending_payload = "busy", "refine", feedback
        self.store.save(session)
        self.work.put(WorkItem(session.chat_id, "refine", feedback))
        self.api.send_message(session.chat_id, "Applying queued refinement feedback.")
