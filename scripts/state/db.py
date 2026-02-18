"""
Iris Task & State Database Helper Module

SQLite-backed persistence for task tracking, activity logging, and state management.
Database: /home/claude/memory/iris.db

Usage from CLI:
    cd /home/claude/memory && python3 -c "from db import *; print(list_tasks())"
"""

import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "iris.db")


def _connect():
    """Return a connection to the database with row_factory set."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now():
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def init_db():
    """Create tables if they don't exist."""
    conn = _connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK(priority IN ('high', 'normal', 'low')),
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')),
            source_email_id TEXT,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            assigned_to TEXT,
            result TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS activity_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            category TEXT NOT NULL
                CHECK(category IN ('email', 'task', 'moltbook', 'error', 'session', 'system', 'improvement')),
            summary TEXT NOT NULL,
            details TEXT,
            email_id TEXT,
            task_id INTEGER,
            FOREIGN KEY (task_id) REFERENCES tasks(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sent_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            to_addr TEXT NOT NULL,
            from_addr TEXT NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            message_id TEXT NOT NULL,
            in_reply_to TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS received_emails (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            message_id TEXT UNIQUE,
            from_addr TEXT,
            to_addr TEXT,
            subject TEXT,
            date TEXT,
            logged_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # Indexes for common queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_category ON activity_log(category)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_timestamp ON activity_log(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sent_emails_to_addr ON sent_emails(to_addr)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sent_emails_subject ON sent_emails(subject)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sent_emails_message_id ON sent_emails(message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sent_emails_in_reply_to ON sent_emails(in_reply_to)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_received_emails_message_id ON received_emails(message_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_received_emails_from_addr ON received_emails(from_addr)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_received_emails_timestamp ON received_emails(timestamp)")

    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Task functions
# ---------------------------------------------------------------------------

def create_task(title, description="", priority="normal", source_email_id=None):
    """Create a new task. Returns the new task ID as a JSON string."""
    now = _now()
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO tasks (created_at, updated_at, priority, status, source_email_id, title, description)
           VALUES (?, ?, ?, 'pending', ?, ?, ?)""",
        (now, now, priority, source_email_id, title, description),
    )
    task_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json.dumps(task_id)


def update_task(task_id, **kwargs):
    """Update any fields on a task. Returns the updated task as JSON.

    Accepted kwargs: status, priority, title, description, source_email_id,
                     assigned_to, result
    """
    allowed = {
        "status", "priority", "title", "description",
        "source_email_id", "assigned_to", "result",
    }
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return json.dumps({"error": "No valid fields to update"})

    fields["updated_at"] = _now()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [int(task_id)]

    conn = _connect()
    conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    conn.commit()

    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    conn.close()
    if row is None:
        return json.dumps({"error": f"Task {task_id} not found"})
    return json.dumps(dict(row))


def get_task(task_id):
    """Return a single task as a JSON dict string."""
    conn = _connect()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    conn.close()
    if row is None:
        return json.dumps(None)
    return json.dumps(dict(row))


def list_tasks(status=None, priority=None):
    """Return tasks matching optional filters as a JSON list of dicts."""
    clauses, params = [], []
    if status is not None:
        clauses.append("status = ?")
        params.append(status)
    if priority is not None:
        clauses.append("priority = ?")
        params.append(priority)

    where = ""
    if clauses:
        where = "WHERE " + " AND ".join(clauses)

    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM tasks {where} ORDER BY id", params
    ).fetchall()
    conn.close()
    return json.dumps([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# Activity log functions
# ---------------------------------------------------------------------------

def log_activity(category, summary, details=None, email_id=None, task_id=None):
    """Log an activity entry. Returns the new log entry ID as JSON."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO activity_log (timestamp, category, summary, details, email_id, task_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (_now(), category, summary, details, email_id, int(task_id) if task_id is not None else None),
    )
    log_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json.dumps(log_id)


def get_recent_activity(limit=20, category=None):
    """Return recent activity log entries as a JSON list of dicts."""
    params = []
    where = ""
    if category is not None:
        where = "WHERE category = ?"
        params.append(category)
    params.append(int(limit))

    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM activity_log {where} ORDER BY id DESC LIMIT ?", params
    ).fetchall()
    conn.close()
    return json.dumps([dict(r) for r in rows])


# ---------------------------------------------------------------------------
# State (key-value) functions
# ---------------------------------------------------------------------------

def set_state(key, value):
    """Set a key-value pair in the state table. Returns JSON confirmation."""
    now = _now()
    conn = _connect()
    conn.execute(
        """INSERT INTO state (key, value, updated_at) VALUES (?, ?, ?)
           ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at""",
        (key, str(value), now),
    )
    conn.commit()
    conn.close()
    return json.dumps({"key": key, "value": str(value), "updated_at": now})


def get_state(key):
    """Get a state value by key. Returns JSON string of the value, or null."""
    conn = _connect()
    row = conn.execute("SELECT value FROM state WHERE key = ?", (key,)).fetchone()
    conn.close()
    if row is None:
        return json.dumps(None)
    return json.dumps(row["value"])


def get_all_state():
    """Return all state as a JSON dict."""
    conn = _connect()
    rows = conn.execute("SELECT key, value, updated_at FROM state ORDER BY key").fetchall()
    conn.close()
    return json.dumps({r["key"]: {"value": r["value"], "updated_at": r["updated_at"]} for r in rows})


# ---------------------------------------------------------------------------
# Sent emails functions
# ---------------------------------------------------------------------------

def log_sent_email(to_addr, from_addr, subject, body, message_id, in_reply_to=None):
    """Log a sent email to the database. Returns the new entry ID as JSON."""
    conn = _connect()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO sent_emails (timestamp, to_addr, from_addr, subject, body, message_id, in_reply_to)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (_now(), to_addr, from_addr, subject, body, message_id, in_reply_to),
    )
    sent_id = cur.lastrowid
    conn.commit()
    conn.close()
    return json.dumps(sent_id)


def get_sent_emails(to_addr=None, subject_match=None, limit=20):
    """Return sent emails as a JSON list of dicts, newest first.

    Args:
        to_addr: Optional filter by recipient address (exact match)
        subject_match: Optional case-insensitive partial subject filter
        limit: Max records to return (default 20)
    """
    clauses, params = [], []
    if to_addr is not None:
        clauses.append("to_addr LIKE ?")
        params.append(f"%{to_addr}%")
    if subject_match is not None:
        clauses.append("subject LIKE ?")
        params.append(f"%{subject_match}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))

    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM sent_emails {where} ORDER BY timestamp DESC LIMIT ?", params
    ).fetchall()
    conn.close()
    return json.dumps([dict(r) for r in rows])


def get_received_emails(from_addr=None, subject_match=None, limit=20):
    """Return received emails logged in iris.db, newest first.

    Args:
        from_addr: Optional case-insensitive partial filter on sender address
        subject_match: Optional case-insensitive partial subject filter
        limit: Max records to return (default 20)
    """
    clauses, params = [], []
    if from_addr is not None:
        clauses.append("from_addr LIKE ?")
        params.append(f"%{from_addr}%")
    if subject_match is not None:
        clauses.append("subject LIKE ?")
        params.append(f"%{subject_match}%")

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(int(limit))

    conn = _connect()
    rows = conn.execute(
        f"SELECT * FROM received_emails {where} ORDER BY timestamp DESC LIMIT ?", params
    ).fetchall()
    conn.close()
    return json.dumps([dict(r) for r in rows])


def get_email_thread(message_id=None, email_address=None, subject_match=None, limit=50):
    """Get email conversation thread combining received and sent emails from iris.db.

    Args:
        message_id: Find all emails in the thread containing this Message-ID
                    (matches sent.message_id, sent.in_reply_to, received.message_id)
        email_address: Filter emails to/from this address (partial match)
        subject_match: Filter by subject line (case-insensitive partial match)
        limit: Maximum number of emails to return (default 50)

    Returns a JSON list of dicts sorted chronologically, each containing:
        - type: 'received' or 'sent'
        - timestamp: UTC ISO timestamp logged
        - from_addr / to_addr / subject / message_id
        - body (sent emails only — body stored in sent_emails table)
        - date (received emails only — original email Date header)
    """
    conn = _connect()
    results = []

    # --- Sent emails ---
    sent_clauses, sent_params = ["1=1"], []

    if message_id:
        sent_clauses.append("(message_id = ? OR in_reply_to = ?)")
        sent_params.extend([message_id, message_id])

    if email_address:
        sent_clauses.append("(to_addr LIKE ? OR from_addr LIKE ?)")
        sent_params.extend([f"%{email_address}%", f"%{email_address}%"])

    if subject_match:
        sent_clauses.append("subject LIKE ?")
        sent_params.append(f"%{subject_match}%")

    sent_rows = conn.execute(
        "SELECT timestamp, to_addr, from_addr, subject, body, message_id, in_reply_to "
        "FROM sent_emails WHERE " + " AND ".join(sent_clauses) +
        " ORDER BY timestamp",
        sent_params,
    ).fetchall()

    for row in sent_rows:
        results.append({
            "type": "sent",
            "timestamp": row["timestamp"],
            "from_addr": row["from_addr"],
            "to_addr": row["to_addr"],
            "subject": row["subject"],
            "body": row["body"],
            "message_id": row["message_id"],
            "in_reply_to": row["in_reply_to"],
        })

    # --- Received emails ---
    recv_clauses, recv_params = ["1=1"], []

    if message_id:
        recv_clauses.append("message_id = ?")
        recv_params.append(message_id)

    if email_address:
        recv_clauses.append("(from_addr LIKE ? OR to_addr LIKE ?)")
        recv_params.extend([f"%{email_address}%", f"%{email_address}%"])

    if subject_match:
        recv_clauses.append("subject LIKE ?")
        recv_params.append(f"%{subject_match}%")

    recv_rows = conn.execute(
        "SELECT timestamp, message_id, from_addr, to_addr, subject, date "
        "FROM received_emails WHERE " + " AND ".join(recv_clauses) +
        " ORDER BY timestamp",
        recv_params,
    ).fetchall()

    for row in recv_rows:
        results.append({
            "type": "received",
            "timestamp": row["timestamp"],
            "from_addr": row["from_addr"],
            "to_addr": row["to_addr"],
            "subject": row["subject"],
            "message_id": row["message_id"],
            "date": row["date"],
        })

    conn.close()

    # Sort chronologically and apply limit
    results.sort(key=lambda x: x["timestamp"])
    return json.dumps(results[-int(limit):])


# ---------------------------------------------------------------------------
# Initialization: create tables on import
# ---------------------------------------------------------------------------
init_db()
