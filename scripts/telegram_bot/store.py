from __future__ import annotations

import sqlite3
import threading
from dataclasses import asdict
from pathlib import Path

from .models import Session
from .schema import SCHEMA, SESSION_COLUMNS


class StateStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.lock = threading.Lock()
        self.connection.executescript(SCHEMA)
        self._ensure_columns()

    def _ensure_columns(self) -> None:
        columns = {row["name"] for row in self.connection.execute("PRAGMA table_info(sessions)")}
        additions = {
            "session_active": "INTEGER NOT NULL DEFAULT 0",
            "job_url": "TEXT NOT NULL DEFAULT ''",
            "careers_url": "TEXT NOT NULL DEFAULT ''",
            "request_id": "INTEGER NOT NULL DEFAULT 0",
            "model_key": "TEXT NOT NULL DEFAULT ''",
        }
        for name, definition in additions.items():
            if name not in columns:
                self.connection.execute(f"ALTER TABLE sessions ADD COLUMN {name} {definition}")
        self.connection.commit()

    def session(self, chat_id: int) -> Session:
        with self.lock:
            row = self.connection.execute(
                "SELECT * FROM sessions WHERE chat_id = ?", (chat_id,),
            ).fetchone()
        if row:
            return Session(**{column: row[column] for column in SESSION_COLUMNS})
        session = Session(chat_id)
        self.save(session)
        return session

    def save(self, session: Session) -> None:
        values = asdict(session)
        columns = list(values)
        placeholders = ", ".join("?" for _ in columns)
        updates = ", ".join(f"{column}=excluded.{column}" for column in columns[1:])
        sql = f"INSERT INTO sessions ({', '.join(columns)}) VALUES ({placeholders}) "
        sql += f"ON CONFLICT(chat_id) DO UPDATE SET {updates}, updated_at=CURRENT_TIMESTAMP"
        with self.lock:
            self.connection.execute(sql, tuple(values[column] for column in columns))
            self.connection.commit()

    def offset(self) -> int | None:
        with self.lock:
            row = self.connection.execute(
                "SELECT value FROM metadata WHERE key = 'offset'"
            ).fetchone()
        return int(row["value"]) if row else None

    def set_offset(self, offset: int) -> None:
        with self.lock:
            self.connection.execute(
                "INSERT INTO metadata(key, value) VALUES('offset', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(offset),),
            )
            self.connection.commit()

    def recover_interrupted(self) -> None:
        with self.lock:
            self.connection.execute(
                "UPDATE sessions SET state='recovery' WHERE state='busy' AND pending_operation != ''"
            )
            self.connection.commit()

    def reset_for_startup(self) -> None:
        with self.lock:
            self.connection.execute(
                "UPDATE sessions SET state='idle', description='', instructions='', "
                "queued_feedback='', pending_operation='', pending_payload='', last_error='', "
                "session_active=0, job_url='', careers_url='', model_key='', "
                "request_id=request_id + 1"
            )
            self.connection.commit()
