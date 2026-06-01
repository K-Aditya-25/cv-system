SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    chat_id INTEGER PRIMARY KEY,
    state TEXT NOT NULL DEFAULT 'idle',
    description TEXT NOT NULL DEFAULT '',
    instructions TEXT NOT NULL DEFAULT '',
    active_job_folder TEXT NOT NULL DEFAULT '',
    latest_pdf TEXT NOT NULL DEFAULT '',
    queued_feedback TEXT NOT NULL DEFAULT '',
    pending_operation TEXT NOT NULL DEFAULT '',
    pending_payload TEXT NOT NULL DEFAULT '',
    last_error TEXT NOT NULL DEFAULT '',
    session_active INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SESSION_COLUMNS = (
    "chat_id", "state", "description", "instructions", "active_job_folder", "latest_pdf",
    "queued_feedback", "pending_operation", "pending_payload", "last_error", "session_active",
)
