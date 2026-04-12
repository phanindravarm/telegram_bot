import os
import sqlite3
import tempfile
import pytest

import db
from datetime import datetime


@pytest.fixture
def temp_db(monkeypatch):
    fd, path = tempfile.mkstemp()
    os.close(fd)

    monkeypatch.setattr(db, "DB_PATH", path)

    db.init_db()

    yield path

    os.remove(path)


@pytest.fixture
def conn(temp_db):
    connection = sqlite3.connect(temp_db)
    yield connection
    connection.close()


def test_table(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'"
    ).fetchall()

    assert ("reminders",) in tables


def test_init_db_idempotent(temp_db):
    db.init_db()
    db.init_db()

    connection = sqlite3.connect(temp_db)
    tables = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='reminders'"
    ).fetchall()
    connection.close()

    assert ("reminders",) in tables


def test_save_reminders(conn):
    trigger_time = datetime(2026, 3, 24, 10, 30, 45, 123456)
    reminder_id = db.save_reminder(123, "Test reminder", trigger_time)

    row = conn.execute(
        "SELECT chat_id, reminder_text, trigger_time FROM reminders WHERE id=?",
        (reminder_id,),
    ).fetchone()

    assert row[0] == 123
    assert row[1] == "Test reminder"
    assert row[2] == trigger_time.isoformat()


def test_get_pending_reminders(temp_db):
    t1 = datetime(2026, 3, 24, 9, 0, 0)
    t2 = datetime(2026, 3, 25, 14, 30, 0)

    id1 = db.save_reminder(1, "A", t1)
    id2 = db.save_reminder(2, "B", t2)

    rows = db.get_pending_reminders()

    assert len(rows) == 2

    ids = [r[0] for r in rows]
    assert id1 in ids
    assert id2 in ids


def test_get_pending_reminders_empty(temp_db):
    rows = db.get_pending_reminders()

    assert rows == []


def test_delete_reminder(conn):
    reminder_id = db.save_reminder(123, "To delete", datetime(2026, 1, 1))

    db.delete_reminder(reminder_id)

    row = conn.execute(
        "SELECT * FROM reminders WHERE id=?",
        (reminder_id,),
    ).fetchone()

    assert row is None


def test_delete_nonexistent_reminder(temp_db):
    db.delete_reminder(99999)


def test_conversation_history_table(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
    ).fetchall()
    assert ("conversation_history",) in tables


def test_token_usage_table(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='token_usage'"
    ).fetchall()
    assert ("token_usage",) in tables


def test_save_message(temp_db, conn):
    db.save_message(100, "user", "Hello", 2)

    row = conn.execute(
        "SELECT chat_id, role, content, token_estimate FROM conversation_history WHERE chat_id = 100"
    ).fetchone()

    assert row[0] == 100
    assert row[1] == "user"
    assert row[2] == "Hello"
    assert row[3] == 2


def test_get_history(temp_db):
    db.save_message(100, "user", "First", 1)
    db.save_message(100, "model", "Reply", 2)
    db.save_message(100, "user", "Second", 1)

    history = db.get_history(100)

    assert len(history) == 3
    assert history[0][0] == "user"
    assert history[0][1] == "First"
    assert history[2][1] == "Second"


def test_get_history_limit(temp_db):
    for i in range(5):
        db.save_message(100, "user", f"msg{i}", 1)

    history = db.get_history(100, limit=3)

    assert len(history) == 3
    # Should return the 3 most recent, oldest first
    assert history[0][1] == "msg2"
    assert history[2][1] == "msg4"


def test_get_history_empty(temp_db):
    assert db.get_history(999) == []


def test_delete_oldest_messages(temp_db):
    db.save_message(100, "user", "old1", 1)
    db.save_message(100, "model", "old2", 1)
    db.save_message(100, "user", "new1", 1)

    db.delete_oldest_messages(100, 2)

    history = db.get_history(100)
    assert len(history) == 1
    assert history[0][1] == "new1"


def test_clear_history(temp_db):
    db.save_message(200, "user", "msg1", 1)
    db.save_message(200, "model", "msg2", 1)
    db.save_message(300, "user", "other", 1)

    db.clear_history(200)

    assert db.get_history(200) == []
    assert len(db.get_history(300)) == 1


def test_log_token_usage(temp_db, conn):
    db.log_token_usage(100, 50, 20)

    row = conn.execute(
        "SELECT chat_id, prompt_tokens, completion_tokens, total_tokens FROM token_usage WHERE chat_id = 100"
    ).fetchone()

    assert row[0] == 100
    assert row[1] == 50
    assert row[2] == 20
    assert row[3] == 70
