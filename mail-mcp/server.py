#!/usr/bin/env python3
"""MCP server for sending, receiving, and managing email via local Postfix."""

import base64
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# Direct sqlite3 logging — avoids circular import issues with db.py
import sqlite3 as _sqlite3

_IRIS_DB_PATH = "/home/claude/iris/scripts/state/iris.db"


def _db_check_duplicate_email(to_addr, subject, body_prefix, within_seconds=300):
    """Check if a very similar email was sent recently. Returns True if duplicate detected."""
    try:
        import datetime as _dt
        conn = _sqlite3.connect(_IRIS_DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        cutoff_dt = datetime.now(timezone.utc) - _dt.timedelta(seconds=within_seconds)
        cutoff_str = cutoff_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        row = conn.execute(
            """SELECT id, timestamp FROM sent_emails
               WHERE to_addr = ?
                 AND subject = ?
                 AND substr(body, 1, 100) = ?
                 AND timestamp >= ?
               LIMIT 1""",
            (to_addr, subject, body_prefix, cutoff_str),
        ).fetchone()
        conn.close()
        if row:
            return True, row[0], row[1]
        return False, None, None
    except Exception as _e:
        print(f"[mail-mcp] DB duplicate check failed: {_e}", file=sys.stderr)
        return False, None, None


def _db_log_sent_email(to_addr, from_addr, subject, body, message_id, in_reply_to=None):
    """Write a sent-email record to iris.db. Silent on failure."""
    try:
        conn = _sqlite3.connect(_IRIS_DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """INSERT INTO sent_emails
               (timestamp, to_addr, from_addr, subject, body, message_id, in_reply_to)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                to_addr,
                from_addr,
                subject,
                body[:500],
                message_id,
                in_reply_to,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as _e:
        print(f"[mail-mcp] DB log_sent_email failed: {_e}", file=sys.stderr)


def _db_log_received_email(message_id, from_addr, to_addr, subject, date):
    """Write a received-email record to iris.db. Silent on failure."""
    try:
        conn = _sqlite3.connect(_IRIS_DB_PATH, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute(
            """CREATE TABLE IF NOT EXISTS received_emails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                message_id TEXT UNIQUE,
                from_addr TEXT,
                to_addr TEXT,
                subject TEXT,
                date TEXT,
                logged_at TEXT DEFAULT (datetime('now'))
            )"""
        )
        conn.execute(
            """INSERT OR IGNORE INTO received_emails
               (timestamp, message_id, from_addr, to_addr, subject, date)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                message_id,
                from_addr,
                to_addr,
                subject,
                date,
            ),
        )
        conn.commit()
        conn.close()
    except Exception as _e:
        print(f"[mail-mcp] DB log_received_email failed: {_e}", file=sys.stderr)

DOMAIN = os.environ.get("IRIS_DOMAIN", "example.com")
DEFAULT_FROM = f"{os.environ.get('ASSISTANT_NAME', 'Iris')} <iris@{DOMAIN}>"
EMAILS_DIR = Path("/home/claude/iris/docs/emails")
INDEX_PATH = EMAILS_DIR / "index.json"
READ_MBOX_SCRIPT = Path(__file__).parent / "read_mbox.py"

# Postmark API configuration
# Load credentials from postmark-account.sh
def _load_postmark_credentials():
    """Load Postmark credentials from shell script."""
    creds_file = Path("/home/claude/iris/docs/services/postmark-account.sh")
    if creds_file.exists():
        with open(creds_file) as f:
            for line in f:
                if line.startswith("export POSTMARK_API_TOKEN="):
                    return line.split("=", 1)[1].strip()
    return os.getenv("POSTMARK_API_TOKEN", "")

POSTMARK_API_TOKEN = _load_postmark_credentials()
POSTMARK_API_URL = "https://api.postmarkapp.com/email"
POSTMARK_STREAM = "outbound"

if not POSTMARK_API_TOKEN:
    import sys
    print("WARNING: POSTMARK_API_TOKEN not found in credentials file or environment", file=sys.stderr)

MAILBOXES = {
    "claude": "/var/mail/claude",
    "root": "/var/mail/root",
}

mcp = FastMCP("email")


# ---------------------------------------------------------------------------
# Index helpers
# ---------------------------------------------------------------------------

def _load_index() -> dict:
    """Load the email index from disk."""
    if INDEX_PATH.exists():
        with open(INDEX_PATH, "r") as f:
            return json.load(f)
    return {}


def _save_index(index: dict) -> None:
    """Atomically save the email index to disk."""
    EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=EMAILS_DIR, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
        os.rename(tmp_path, INDEX_PATH)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _hash_message_id(message_id: str) -> str:
    """Return first 12 chars of SHA-256 of the Message-ID."""
    return hashlib.sha256(message_id.encode()).hexdigest()[:12]


def _sanitize_subject(subject: str) -> str:
    """Sanitize subject for use in filename."""
    # Remove Re:/Fwd: prefixes
    s = re.sub(r"^(Re|Fwd|Fw)\s*:\s*", "", subject, flags=re.IGNORECASE)
    # Keep only alphanumeric, spaces, hyphens
    s = re.sub(r"[^a-zA-Z0-9 \-]", "", s)
    # Collapse whitespace to underscores
    s = re.sub(r"\s+", "_", s.strip())
    # Truncate
    return s[:50] if s else "no_subject"


def _parse_email_date(date_str: str) -> datetime | None:
    """Try to parse an email date string."""
    if not date_str:
        return None
    # Try email.utils first
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        pass
    return None


def _make_filename(date_str: str, subject: str, hash12: str) -> str:
    """Generate a deterministic filename for an email."""
    dt = _parse_email_date(date_str)
    if dt:
        prefix = dt.strftime("%Y%m%d_%H%M%S")
    else:
        prefix = "00000000_000000"
    safe_subject = _sanitize_subject(subject)
    return f"{prefix}_{safe_subject}_{hash12}.txt"


def _write_email_file(filename: str, msg: dict) -> None:
    """Write an individual email to a .txt file."""
    EMAILS_DIR.mkdir(parents=True, exist_ok=True)
    filepath = EMAILS_DIR / filename
    with open(filepath, "w") as f:
        f.write(f"Message-ID: {msg['message_id']}\n")
        if msg.get("in_reply_to"):
            f.write(f"In-Reply-To: {msg['in_reply_to']}\n")
        if msg.get("references"):
            f.write(f"References: {msg['references']}\n")
        f.write(f"Date: {msg['date']}\n")
        f.write(f"From: {msg['from']}\n")
        f.write(f"To: {msg['to']}\n")
        f.write(f"Subject: {msg['subject']}\n")
        # Write attachment summary if present
        attachments = msg.get("attachments", [])
        if attachments:
            f.write(f"Attachments: {len(attachments)} file(s)\n")
            for att in attachments:
                size_kb = att.get("size", 0) / 1024
                f.write(f"  - {att['filename']} ({att['content_type']}, {size_kb:.1f} KB)\n")
                if att.get("path"):
                    f.write(f"    Saved: {att['path']}\n")
                elif att.get("error"):
                    f.write(f"    Error: {att['error']}\n")
        f.write(f"{'=' * 60}\n\n")
        f.write(msg.get("body", "").strip())
        f.write("\n")


def _read_mbox(path: str) -> list[dict]:
    """Read an mbox file, using sudo if needed for root mailbox."""
    if not os.path.exists(path):
        return []

    # Check if we can read it directly
    if os.access(path, os.R_OK):
        cmd = ["python3", str(READ_MBOX_SCRIPT), path]
    else:
        cmd = ["sudo", "python3", str(READ_MBOX_SCRIPT), path]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
    )

    if result.returncode != 0:
        raise RuntimeError(f"Failed to read {path}: {result.stderr}")

    data = json.loads(result.stdout)
    if isinstance(data, dict) and "error" in data:
        raise RuntimeError(f"Error reading {path}: {data['error']}")

    return data


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------

@mcp.tool()
def send_email(to: str, subject: str, body: str, from_addr: str = DEFAULT_FROM, cc: str = None, is_reply: bool = False, in_reply_to: str = None, references: str = None, attachments: list = None) -> str:
    """Send an email using Postmark API only (no sendmail fallback).

    POLICY: Do NOT use SMTP/sendmail for sending emails! Postmark API only.
    - RECEIVE: SMTP (local mail server)
    - SEND: Postmark API only (reliable, reputable, passes DKIM/SPF)

    THREADING POLICY: Explicitly indicate if this is a reply to thread properly.
    - For NEW threads: set is_reply=False (default) and do NOT provide in_reply_to/references
    - For REPLIES: set is_reply=True and MUST provide in_reply_to (references auto-populated if omitted)

    Args:
        to: Recipient email address (e.g. user@example.com)
        subject: Email subject line
        body: Plain text email body
        from_addr: Sender address (defaults to Iris <claude@example.com>)
        cc: Optional CC address (e.g. user2@example.com)
        is_reply: If True, this is a reply to an existing email (requires in_reply_to)
        in_reply_to: Message-ID of the email being replied to (required when is_reply=True)
        references: Space-separated chain of Message-IDs in conversation (auto-populated from in_reply_to if omitted)
        attachments: Optional list of file paths to attach to the email
    """
    # THREADING VALIDATION: Enforce threading policy at runtime
    if is_reply:
        if not in_reply_to:
            raise ValueError(
                "Threading error: is_reply=True requires in_reply_to parameter. "
                "Provide the Message-ID of the email you're replying to."
            )
    else:
        # Not a reply - warn if threading headers provided (likely a mistake)
        if in_reply_to or references:
            raise ValueError(
                "Threading error: is_reply=False but in_reply_to/references provided. "
                "Set is_reply=True to send a threaded reply, or remove threading headers for a new thread."
            )

    # Idempotency guard: skip if a very similar email was sent in the last 5 minutes
    body_prefix = body[:100]
    is_dup, dup_id, dup_ts = _db_check_duplicate_email(to, subject, body_prefix, within_seconds=300)
    if is_dup:
        warning = (
            f"[mail-mcp] DUPLICATE EMAIL BLOCKED: to={to!r} subject={subject!r} "
            f"matches sent_emails row {dup_id} at {dup_ts}. Skipping send."
        )
        print(warning, file=sys.stderr)
        return (
            f"[SKIPPED - DUPLICATE] Email to {to!r} with subject {subject!r} was already sent "
            f"at {dup_ts} (DB row {dup_id}). Not sending again within 5-minute window."
        )

    msg_id = f"<mcp-{int(time.time())}@{DOMAIN}>"

    # Build payload with optional reply headers
    payload_dict = {
        "From": from_addr,
        "To": to,
        "Subject": subject,
        "TextBody": body,
        "MessageStream": POSTMARK_STREAM,
    }

    # Add CC if provided
    if cc:
        payload_dict["Cc"] = cc

    # Add reply headers for email threading (only if this is a reply)
    if is_reply and in_reply_to:
        headers_list = []
        # Always add In-Reply-To for replies
        headers_list.append({"Name": "In-Reply-To", "Value": in_reply_to})

        # Auto-populate references from in_reply_to if not explicitly provided
        if not references:
            references = in_reply_to
        headers_list.append({"Name": "References", "Value": references})

        payload_dict["Headers"] = headers_list

    # Add attachments if provided
    if attachments:
        att_list = []
        for file_path in attachments:
            file_path = Path(file_path)
            if not file_path.exists():
                raise ValueError(f"Attachment file not found: {file_path}")
            if not file_path.is_file():
                raise ValueError(f"Attachment path is not a file: {file_path}")

            # Determine content type
            content_type, _ = mimetypes.guess_type(str(file_path))
            if not content_type:
                content_type = "application/octet-stream"

            # Read and base64-encode the file
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")

            att_list.append({
                "Name": file_path.name,
                "Content": encoded,
                "ContentType": content_type,
            })

        payload_dict["Attachments"] = att_list

    payload = json.dumps(payload_dict).encode("utf-8")

    req = urllib.request.Request(
        POSTMARK_API_URL,
        data=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "X-Postmark-Server-Token": POSTMARK_API_TOKEN,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp_body = json.loads(resp.read().decode("utf-8"))
            pm_message_id = resp_body.get("MessageID", msg_id)

            # Log sent email to iris.db (fire-and-forget; silent on failure)
            _db_log_sent_email(
                to_addr=to,
                from_addr=from_addr,
                subject=subject,
                body=body,
                message_id=pm_message_id,
                in_reply_to=in_reply_to,
            )

            att_count = len(attachments) if attachments else 0
            att_info = f" with {att_count} attachment(s)" if att_count else ""
            return (
                f"Email sent to {to} with subject \"{subject}\"{att_info} "
                f"via Postmark (MessageID: {pm_message_id})"
            )

    except urllib.error.HTTPError as exc:
        # HTTP error from Postmark API
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(
            f"Postmark API HTTP error {exc.code}: {exc.reason}. "
            f"Response: {error_body}"
        ) from exc

    except urllib.error.URLError as exc:
        # Network/connection error
        raise RuntimeError(
            f"Postmark API connection failed: {exc.reason}"
        ) from exc

    except Exception as exc:
        # Any other error
        raise RuntimeError(
            f"Postmark API request failed: {str(exc)}"
        ) from exc

@mcp.tool()
def check_email(mailbox_name: str = "root", limit: int = 10) -> str:
    """Check a local mbox mailbox for received emails (raw mbox view).

    Args:
        mailbox_name: Which mailbox to check - "root" or "claude" (default "root")
        limit: Maximum number of recent messages to return (default 10)
    """
    path = MAILBOXES.get(mailbox_name)
    if not path:
        return f"ERROR: Unknown mailbox '{mailbox_name}'. Available: {', '.join(MAILBOXES.keys())}"

    try:
        messages = _read_mbox(path)
    except Exception as e:
        return f"ERROR: Could not read mailbox: {e}"

    if not messages:
        return f"Mailbox '{mailbox_name}' is empty."

    recent = messages[-limit:]
    output_parts = [f"Showing {len(recent)} of {len(messages)} messages in '{mailbox_name}':\n"]

    for i, msg in enumerate(recent, 1):
        body = msg.get("body", "").strip()
        if len(body) > 1000:
            body = body[:1000] + "\n... (truncated)"

        msg_text = f"--- Message {i} ---\n"
        msg_text += f"Date: {msg['date']}\n"
        msg_text += f"From: {msg['from']}\n"
        msg_text += f"To: {msg['to']}\n"
        msg_text += f"Subject: {msg['subject']}\n"
        msg_text += f"Message-ID: {msg['message_id']}\n"
        if msg.get("in_reply_to"):
            msg_text += f"In-Reply-To: {msg['in_reply_to']}\n"
        if msg.get("references"):
            msg_text += f"References: {msg['references']}\n"
        msg_text += f"\n{body}\n"

        output_parts.append(msg_text)

    return "\n".join(output_parts)


@mcp.tool()
def sync_emails() -> str:
    """Scan all mbox files for new emails, extract them to individual .txt files, and update the index.

    Returns a summary of what was found and synced.
    """
    index = _load_index()
    new_count = 0
    errors = []

    for mbox_name, mbox_path in MAILBOXES.items():
        try:
            messages = _read_mbox(mbox_path)
        except Exception as e:
            errors.append(f"Error reading {mbox_name}: {e}")
            continue

        for msg in messages:
            message_id = msg.get("message_id", "").strip()
            if not message_id:
                # Generate a fallback ID from content
                content = f"{msg.get('from', '')}{msg.get('date', '')}{msg.get('subject', '')}"
                message_id = f"<generated-{hashlib.sha256(content.encode()).hexdigest()[:16]}>"
                msg["message_id"] = message_id

            hash12 = _hash_message_id(message_id)

            # Skip if already in index
            if hash12 in index:
                continue

            # New email - extract to file
            filename = _make_filename(msg.get("date", ""), msg.get("subject", ""), hash12)
            try:
                _write_email_file(filename, msg)
            except Exception as e:
                errors.append(f"Error writing {filename}: {e}")
                continue

            # Add to index
            index[hash12] = {
                "message_id": message_id,
                "in_reply_to": msg.get("in_reply_to", ""),
                "references": msg.get("references", ""),
                "from": msg.get("from", ""),
                "to": msg.get("to", ""),
                "subject": msg.get("subject", ""),
                "date": msg.get("date", ""),
                "read": False,
                "mailbox": mbox_name,
                "filename": filename,
                "action_todo": "",
                "action_taken": "",
                "attachments": msg.get("attachments", []),
            }

            # Log received email to iris.db (fire-and-forget; silent on failure)
            _db_log_received_email(
                message_id=message_id,
                from_addr=msg.get("from", ""),
                to_addr=msg.get("to", ""),
                subject=msg.get("subject", ""),
                date=msg.get("date", ""),
            )

            new_count += 1

    _save_index(index)

    parts = [f"Sync complete. {new_count} new email(s) found. {len(index)} total in index."]
    if errors:
        parts.append(f"\nErrors ({len(errors)}):")
        for err in errors:
            parts.append(f"  - {err}")

    return "\n".join(parts)


@mcp.tool()
def check_new_emails(auto_sync: bool = True) -> str:
    """Check for new/unread emails. This is the main tool for ongoing email monitoring.

    Args:
        auto_sync: If True (default), sync from mbox files first to pick up new deliveries.
    """
    if auto_sync:
        sync_result = sync_emails()
    else:
        sync_result = None

    index = _load_index()
    unread = {k: v for k, v in index.items() if not v.get("read", False)}

    if not unread:
        msg = "No unread emails."
        if sync_result and "new email" in sync_result:
            msg = sync_result + "\n\n" + msg
        return msg

    parts = [f"{len(unread)} unread email(s):\n"]

    # Sort by date
    sorted_unread = sorted(unread.items(), key=lambda x: x[1].get("date", ""))

    for hash12, entry in sorted_unread:
        parts.append(
            f"  [{hash12}] {entry['date']}\n"
            f"    From: {entry['from']}\n"
            f"    Subject: {entry['subject']}\n"
        )

    if sync_result and "new email" in sync_result:
        parts.insert(0, sync_result + "\n")

    return "\n".join(parts)


@mcp.tool()
def read_email(email_id: str) -> str:
    """Read a specific email by its hash ID and mark it as read.

    Args:
        email_id: The 12-character hash ID of the email (shown in square brackets in listings).
    """
    index = _load_index()

    if email_id not in index:
        return f"ERROR: Email ID '{email_id}' not found. Use list_emails() or check_new_emails() to see available IDs."

    entry = index[email_id]
    filepath = EMAILS_DIR / entry["filename"]

    if not filepath.exists():
        return f"ERROR: Email file '{entry['filename']}' not found on disk."

    with open(filepath, "r") as f:
        content = f.read()

    # Mark as read
    if not entry.get("read", False):
        entry["read"] = True
        _save_index(index)

    # Append attachment info if present (and not already in file body)
    attachments = entry.get("attachments", [])
    if attachments:
        att_lines = [f"\n{'=' * 60}", f"Attachments ({len(attachments)}):"]
        for att in attachments:
            size_kb = att.get("size", 0) / 1024
            att_lines.append(f"  - {att['filename']} | {att['content_type']} | {size_kb:.1f} KB")
            if att.get("path"):
                att_lines.append(f"    Path: {att['path']}")
            if att.get("error"):
                att_lines.append(f"    Error: {att['error']}")
        content += "\n".join(att_lines) + "\n"

    # Append action tracking fields if they exist
    action_parts = []
    if entry.get("action_todo"):
        action_parts.append(f"Action TODO: {entry['action_todo']}")
    if entry.get("action_taken"):
        action_parts.append(f"Action Taken: {entry['action_taken']}")
    if action_parts:
        content += f"\n{'=' * 60}\n" + "\n".join(action_parts) + "\n"

    return content


@mcp.tool()
def mark_email(email_id: str, read: bool = True) -> str:
    """Toggle the read/unread status of an email.

    Args:
        email_id: The 12-character hash ID of the email.
        read: Set to True to mark as read, False to mark as unread.
    """
    index = _load_index()

    if email_id not in index:
        return f"ERROR: Email ID '{email_id}' not found."

    index[email_id]["read"] = read
    _save_index(index)

    status = "read" if read else "unread"
    return f"Email [{email_id}] '{index[email_id]['subject']}' marked as {status}."


@mcp.tool()
def update_email_action(email_id: str, action_todo: str = None, action_taken: str = None) -> str:
    """Update the action tracking fields on an email.

    Args:
        email_id: The 12-character hash ID of the email.
        action_todo: If provided, set the action_todo field to this value.
        action_taken: If provided, set the action_taken field to this value.
    """
    index = _load_index()

    if email_id not in index:
        return f"ERROR: Email ID '{email_id}' not found."

    if action_todo is None and action_taken is None:
        return "No updates provided. Pass action_todo and/or action_taken."

    if action_todo is not None:
        index[email_id]["action_todo"] = action_todo
    if action_taken is not None:
        index[email_id]["action_taken"] = action_taken

    _save_index(index)

    parts = [f"Email [{email_id}] '{index[email_id]['subject']}' action fields updated:"]
    if action_todo is not None:
        parts.append(f"  action_todo: {action_todo}")
    if action_taken is not None:
        parts.append(f"  action_taken: {action_taken}")
    return "\n".join(parts)


@mcp.tool()
def list_emails(mailbox: str = "all", only_unread: bool = False, limit: int = 20) -> str:
    """List emails from the index with flexible filtering.

    Args:
        mailbox: Filter by mailbox name ("claude", "root", or "all"). Default "all".
        only_unread: If True, only show unread emails. Default False.
        limit: Maximum number of emails to return. Default 20.
    """
    index = _load_index()

    if not index:
        return "No emails in index. Run sync_emails() first."

    # Filter
    filtered = {}
    for k, v in index.items():
        if mailbox != "all" and v.get("mailbox") != mailbox:
            continue
        if only_unread and v.get("read", False):
            continue
        filtered[k] = v

    if not filtered:
        return f"No emails match filters (mailbox={mailbox}, only_unread={only_unread})."

    # Sort by date descending (newest first)
    sorted_emails = sorted(filtered.items(), key=lambda x: x[1].get("date", ""), reverse=True)
    shown = sorted_emails[:limit]

    parts = [f"Showing {len(shown)} of {len(filtered)} emails (total in index: {len(index)}):\n"]

    for hash12, entry in shown:
        read_marker = " " if entry.get("read", False) else "*"
        att_count = len(entry.get("attachments", []))
        att_marker = f" [+{att_count} attachment(s)]" if att_count else ""
        entry_text = (
            f"  {read_marker} [{hash12}] {entry.get('date', 'no date')}\n"
            f"    From: {entry.get('from', '?')} | To: {entry.get('to', '?')}\n"
            f"    Subject: {entry.get('subject', '(no subject)')}{att_marker}\n"
            f"    Mailbox: {entry.get('mailbox', '?')}\n"
        )
        if entry.get("action_todo"):
            entry_text += f"    Action TODO: {entry['action_todo']}\n"
        if entry.get("action_taken"):
            entry_text += f"    Action Taken: {entry['action_taken']}\n"
        parts.append(entry_text)

    parts.append("(* = unread)")
    return "\n".join(parts)


@mcp.tool()
def check_mail_log(lines: int = 20) -> str:
    """Check recent mail server logs for delivery status.

    Args:
        lines: Number of recent log lines to return (default 20)
    """
    result = subprocess.run(
        ["tail", f"-{lines}", "/var/log/mail.log"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        return f"ERROR: {result.stderr}"
    return result.stdout


@mcp.tool()
def generate_image(
    image_type: str,
    output_path: str,
    text: str = "",
    title: str = "",
    subtitle: str = "",
    data: dict = None,
    width: int = 800,
    height: int = 400,
) -> str:
    """Generate an image using Pillow and save it to disk.

    Can be used to create images for attaching to emails (charts, banners, text notices).

    Args:
        image_type: Type of image - "text", "banner", or "chart"
        output_path: Full path where the image should be saved (PNG)
        text: Main body text (for "text" and "banner" types)
        title: Title text (for "text" and "chart" types)
        subtitle: Subtitle text (for "banner" type)
        data: Dict of {label: value} pairs for "chart" type
        width: Image width in pixels (default 800)
        height: Image height in pixels (default 400 for text/chart, 200 for banner)

    Returns:
        Path to the saved image file and its size.

    Examples:
        generate_image(image_type="text", text="Hello!", output_path="/tmp/hello.png", title="Greeting")
        generate_image(image_type="banner", text="Iris Mail", subtitle="Ready", output_path="/tmp/banner.png")
        generate_image(image_type="chart", data={"Sent": 10, "Received": 5}, title="Stats", output_path="/tmp/chart.png")
    """
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from generate_image import generate_text_image, generate_bar_chart, generate_banner
    except ImportError as e:
        return f"ERROR: Could not import image generation module: {e}"

    try:
        if image_type == "text":
            path = generate_text_image(
                text=text,
                output_path=output_path,
                width=width,
                height=height,
                title=title or None,
            )
        elif image_type == "banner":
            path = generate_banner(
                text=text,
                output_path=output_path,
                width=width,
                height=height if height != 400 else 200,
                subtitle=subtitle or None,
            )
        elif image_type == "chart":
            path = generate_bar_chart(
                data=data or {},
                output_path=output_path,
                title=title or "Chart",
                width=width,
                height=height if height != 400 else 500,
            )
        else:
            return f"ERROR: Unknown image_type '{image_type}'. Use: text, banner, chart"

        size = os.path.getsize(path)
        return f"Image generated: {path} ({size:,} bytes)"

    except Exception as e:
        return f"ERROR generating image: {e}"


# ---------------------------------------------------------------------------
# Task & State MCP Tools (wrappers around iris/scripts/state/db.py)
# ---------------------------------------------------------------------------

def _load_db():
    """Import db module from iris scripts. Returns module or raises ImportError."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "iris_db", "/home/claude/iris/scripts/state/db.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@mcp.tool()
def list_tasks(status: str = None, priority: str = None) -> str:
    """List Iris's tasks from the database.

    Returns a JSON string — a list of task dicts, each with fields:
      id, title, description, status, priority, created_at, updated_at,
      source_email_id, assigned_to, result.

    Args:
        status: Optional filter — one of: pending, in_progress, completed, cancelled
        priority: Optional filter — one of: high, normal, low
    """
    try:
        db = _load_db()
        return db.list_tasks(status=status, priority=priority)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def create_task(title: str, description: str = "", priority: str = "normal", source_email_id: str = None) -> str:
    """Create a new task in Iris's database.

    Returns a JSON string containing the new task's integer ID.

    Args:
        title: Short title for the task (required)
        description: Full description / details of what needs to be done
        priority: One of: high, normal, low (default: normal)
        source_email_id: Optional 12-char email hash ID that triggered this task
    """
    try:
        db = _load_db()
        return db.create_task(
            title=title,
            description=description,
            priority=priority,
            source_email_id=source_email_id,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def update_task(task_id: int, status: str = None, priority: str = None, title: str = None, description: str = None, result: str = None, assigned_to: str = None) -> str:
    """Update fields on an existing task.

    Returns a JSON string of the updated task dict, or {"error": "..."} on failure.

    Args:
        task_id: Integer ID of the task to update (required)
        status: New status — one of: pending, in_progress, completed, cancelled
        priority: New priority — one of: high, normal, low
        title: New task title
        description: New task description
        result: Result/output text once the task is complete
        assigned_to: Who or what is handling this task
    """
    try:
        db = _load_db()
        kwargs = {}
        if status is not None:
            kwargs["status"] = status
        if priority is not None:
            kwargs["priority"] = priority
        if title is not None:
            kwargs["title"] = title
        if description is not None:
            kwargs["description"] = description
        if result is not None:
            kwargs["result"] = result
        if assigned_to is not None:
            kwargs["assigned_to"] = assigned_to
        if not kwargs:
            return json.dumps({"error": "No fields provided to update"})
        return db.update_task(task_id, **kwargs)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_recent_activity(limit: int = 20, category: str = None) -> str:
    """Fetch recent entries from Iris's activity log.

    Returns a JSON string — a list of activity dicts, newest first, each with:
      id, timestamp, category, summary, details, email_id, task_id.

    Valid categories: email, task, moltbook, error, session, system, improvement

    Args:
        limit: Maximum number of entries to return (default 20)
        category: Optional filter by category name
    """
    try:
        db = _load_db()
        return db.get_recent_activity(limit=limit, category=category)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_task_state() -> str:
    """Get a summary of Iris's current state: pending/in-progress tasks and recent activity.

    Returns a JSON string with keys:
      - pending_tasks: list of pending task dicts
      - in_progress_tasks: list of in-progress task dicts
      - recent_activity: last 10 activity log entries
      - task_counts: dict with counts by status

    All db functions return JSON strings — this tool parses and assembles them.
    """
    try:
        db = _load_db()

        pending = json.loads(db.list_tasks(status="pending"))
        in_progress = json.loads(db.list_tasks(status="in_progress"))
        completed = json.loads(db.list_tasks(status="completed"))
        cancelled = json.loads(db.list_tasks(status="cancelled"))
        recent = json.loads(db.get_recent_activity(limit=10))

        summary = {
            "pending_tasks": pending,
            "in_progress_tasks": in_progress,
            "recent_activity": recent,
            "task_counts": {
                "pending": len(pending),
                "in_progress": len(in_progress),
                "completed": len(completed),
                "cancelled": len(cancelled),
            },
        }
        return json.dumps(summary, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def log_activity(category: str, summary: str, details: str = None, email_id: str = None, task_id: int = None) -> str:
    """Log an activity entry to Iris's activity log.

    Returns a JSON string containing the new log entry's integer ID.

    Valid categories: email, task, moltbook, error, session, system, improvement

    Args:
        category: Activity category (required) — one of the valid categories above
        summary: Short one-line description of what happened (required)
        details: Optional longer description / context
        email_id: Optional 12-char email hash ID related to this activity
        task_id: Optional integer task ID related to this activity
    """
    try:
        db = _load_db()
        return db.log_activity(
            category=category,
            summary=summary,
            details=details,
            email_id=email_id,
            task_id=task_id,
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_state_value(key: str) -> str:
    """Get a key-value pair from Iris's persistent state store.

    Returns a JSON string of the value (string), or JSON null if not set.

    Args:
        key: The state key to retrieve
    """
    try:
        db = _load_db()
        return db.get_state(key)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def set_state_value(key: str, value: str) -> str:
    """Set a key-value pair in Iris's persistent state store.

    Returns a JSON dict confirming the write: {"key": ..., "value": ..., "updated_at": ...}

    Args:
        key: The state key to set
        value: The string value to store
    """
    try:
        db = _load_db()
        return db.set_state(key, value)
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
def get_all_state_values() -> str:
    """Return all key-value pairs from Iris's persistent state store.

    Returns a JSON dict mapping key -> {"value": ..., "updated_at": ...}
    """
    try:
        db = _load_db()
        return db.get_all_state()
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    mcp.run(transport="stdio")
