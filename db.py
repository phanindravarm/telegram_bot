import os
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "reminders.db")


def _connect():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _connect()
    conn.execute(
        """CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            reminder_text TEXT NOT NULL,
            trigger_time TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            token_estimate INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_conv_chat_id ON conversation_history(chat_id)"
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS token_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            prompt_tokens INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        """CREATE TABLE IF NOT EXISTS rag_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            source TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding TEXT NOT NULL,
            ingested_at TEXT NOT NULL
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_rag_chat_id ON rag_chunks(chat_id)"
    )
    conn.commit()
    conn.close()


def save_reminder(chat_id, reminder_text, trigger_time):
    conn = _connect()
    cursor = conn.execute(
        "INSERT INTO reminders (chat_id, reminder_text, trigger_time) VALUES (?, ?, ?)",
        (chat_id, reminder_text, trigger_time.isoformat()),
    )
    reminder_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return reminder_id


def delete_reminder(reminder_id):
    conn = _connect()
    conn.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
    conn.commit()
    conn.close()


def save_message(chat_id, role, content, token_estimate):
    conn = _connect()
    conn.execute(
        "INSERT INTO conversation_history (chat_id, role, content, token_estimate, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, role, content, token_estimate, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_history(chat_id, limit=50):
    conn = _connect()
    rows = conn.execute(
        "SELECT role, content, token_estimate FROM conversation_history WHERE chat_id = ? ORDER BY id DESC LIMIT ?",
        (chat_id, limit),
    ).fetchall()
    conn.close()
    rows.reverse()
    return rows


def delete_oldest_messages(chat_id, count):
    conn = _connect()
    conn.execute(
        "DELETE FROM conversation_history WHERE id IN (SELECT id FROM conversation_history WHERE chat_id = ? ORDER BY id ASC LIMIT ?)",
        (chat_id, count),
    )
    conn.commit()
    conn.close()


def clear_history(chat_id):
    conn = _connect()
    conn.execute("DELETE FROM conversation_history WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def log_token_usage(chat_id, prompt_tokens, completion_tokens):
    conn = _connect()
    conn.execute(
        "INSERT INTO token_usage (chat_id, prompt_tokens, completion_tokens, total_tokens, created_at) VALUES (?, ?, ?, ?, ?)",
        (chat_id, prompt_tokens, completion_tokens, prompt_tokens + completion_tokens, datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    conn.close()


def get_pending_reminders():
    conn = _connect()
    rows = conn.execute(
        "SELECT id, chat_id, reminder_text, trigger_time FROM reminders"
    ).fetchall()
    conn.close()
    return rows
