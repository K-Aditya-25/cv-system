from queue import Queue
from scripts.job_creation.constants import DEFAULT_CV_REQUIREMENTS
from scripts.job_creation.model_catalog import model_menu_text
from .api import TelegramApi
from .controller_actions import HELP, append, clear, hard_reset, resend, retry_pending, save, start
from .controller_jobs import add_text_document, begin_refine, choose_refine
from .controller_models import choose_model, start_create
from .controller_url import route_url_text, status_text
from .models import Session, WorkItem
from .store import StateStore
class BotController:
    def __init__(self, api: TelegramApi, store: StateStore, work: Queue[WorkItem], allowed: set[int]):
        self.api, self.store, self.work, self.allowed = api, store, work, allowed
    def handle(self, update: dict) -> None:
        message = update.get("message", {})
        chat, text = message.get("chat", {}), message.get("text", "").strip()
        chat_id = chat.get("id")
        if not chat_id or chat.get("type") != "private":
            return
        if text == "/whoami":
            self.api.send_message(chat_id, f"Your Telegram chat ID is {chat_id}.")
            return
        if chat_id not in self.allowed:
            self.api.send_message(chat_id, "This bot is private. Use /whoami to find your chat ID.")
            return
        session = self.store.session(chat_id)
        if text.startswith("/"):
            self._command(session, text.split()[0].lower())
        elif message.get("document"):
            add_text_document(self.api, self.store, session, message["document"])
        elif text:
            self._text(session, text)
    def _command(self, session: Session, command: str) -> None:
        if command in {"/start", "/help"}:
            self.api.send_message(session.chat_id, HELP)
        elif command == "/new" and session.state != "busy":
            clear(session, "collecting_description", active=1)
            self._save(session, "Send a job URL, paste the description, or send a .txt file. Use /done after text.")
        elif command == "/refine" and session.state != "busy":
            begin_refine(self.api, self.store, session)
        elif command == "/done":
            self._done(session)
        elif command == "/none" and session.state == "collecting_instructions":
            start_create(self.api, self.store, self.work, session, DEFAULT_CV_REQUIREMENTS)
        elif command == "/cancel" and session.state != "busy":
            clear(session)
            self._save(session, "Draft cleared.")
        elif command == "/reset" and session.state != "busy":
            hard_reset(session)
            self._save(session, "Session reset. No CV is active.")
        elif command == "/status":
            self.api.send_message(session.chat_id, status_text(session))
        elif command == "/resend":
            resend(self.api, session)
        elif session.state == "busy":
            self.api.send_message(session.chat_id, "A CV operation is running. Please wait.")
        else:
            self.api.send_message(session.chat_id, "Command unavailable in the current state. Use /help.")
    def _done(self, session: Session) -> None:
        if session.state == "collecting_description" and session.description:
            session.state = "choosing_model"
            self._save(session, model_menu_text())
        elif session.state == "choosing_model":
            self.api.send_message(session.chat_id, model_menu_text())
        elif session.state == "collecting_instructions":
            start_create(self.api, self.store, self.work, session, session.instructions or DEFAULT_CV_REQUIREMENTS)
        elif session.state == "recovery" and session.pending_operation:
            retry_pending(self.api, self.store, self.work, session)
        else:
            self.api.send_message(session.chat_id, "There is nothing ready to submit.")
    def _text(self, session: Session, text: str) -> None:
        if route_url_text(self.api, self.store, self.work, session, text):
            return
        if session.state == "choosing_refine":
            choose_refine(self.api, self.store, session, text)
        elif session.state == "choosing_model":
            choose_model(self.api, self.store, session, text)
        elif not session.session_active:
            self.api.send_message(session.chat_id, "Use /new before sending a job description.")
        elif session.state == "busy":
            session.queued_feedback = append(session.queued_feedback, text)
            self._save(session, "Feedback queued for the next refinement.")
        elif session.state == "resolving_job_url":
            self.api.send_message(session.chat_id, "Still checking the URL. Use /cancel or /new to stop it.")
        elif session.state == "collecting_description":
            session.description = append(session.description, text)
            self._save(session, "Description chunk added.")
        elif session.state == "collecting_instructions":
            session.instructions = append(session.instructions, text)
            self._save(session, "Instruction chunk added.")
        elif session.active_job_folder or session.pdf_path:
            if not session.active_job_folder and session.pdf_path:
                session.active_job_folder = str(session.pdf_path.parent)
                self.store.save(session)
            start(self.api, self.store, self.work, session, "refine", text, "Refining CV.")
        else:
            self.api.send_message(session.chat_id, "Use /new before sending a job description.")
    def _save(self, session: Session, notice: str) -> None:
        save(self.api, self.store, session, notice)
