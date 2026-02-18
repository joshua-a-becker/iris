#!/usr/bin/env python3
"""
Matrix notification script — runs via cron, sends email if new messages.
Piggybacks on the email watchdog for notification delivery.
"""

import json
import os
import sys
import urllib.request
import urllib.error
from datetime import datetime

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CREDENTIALS_FILE = "/home/claude/.config/iris/matrix_credentials.json"
SYNC_TOKEN_FILE = "/tmp/iris_matrix_last_sync"
IRIS_USER_ID = "@iris:matrix.example.com"
NOTIFY_EMAIL = "iris@[YOUR_DOMAIN]"

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
sys.path.append('/home/claude/iris/mail-mcp')
from server import send_email


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def load_credentials():
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)


def read_sync_token():
    if os.path.exists(SYNC_TOKEN_FILE):
        with open(SYNC_TOKEN_FILE) as f:
            token = f.read().strip()
            return token if token else None
    return None


def write_sync_token(token):
    with open(SYNC_TOKEN_FILE, "w") as f:
        f.write(token)


def matrix_sync(homeserver, access_token, since=None):
    params = "timeout=0"
    if since:
        params += f"&since={urllib.parse.quote(since)}"
    url = f"{homeserver}/_matrix/client/v3/sync?{params}"

    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


# ---------------------------------------------------------------------------
# Need to import urllib.parse for the quote call
# ---------------------------------------------------------------------------
import urllib.parse


def collect_new_messages(sync_data):
    """
    Walk sync response and collect messages not sent by Iris herself.
    Returns a list of dicts: {room_id, sender, body, timestamp}
    """
    messages = []
    rooms = sync_data.get("rooms", {})
    join = rooms.get("join", {})

    for room_id, room_data in join.items():
        timeline = room_data.get("timeline", {})
        events = timeline.get("events", [])
        for event in events:
            if event.get("type") != "m.room.message":
                continue
            sender = event.get("sender", "")
            if sender == IRIS_USER_ID:
                continue
            content = event.get("content", {})
            msg_type = content.get("msgtype", "")
            if msg_type != "m.text":
                continue
            body = content.get("body", "").strip()
            if not body:
                continue
            ts = event.get("origin_server_ts", 0)
            messages.append({
                "room_id": room_id,
                "sender": sender,
                "body": body,
                "timestamp": ts,
                "event_id": event.get("event_id", ""),  # for threaded replies
            })

    return messages


def format_email_body(messages, room_display_names):
    lines = [
        "New Matrix message(s) received:\n",
        "=" * 40,
    ]
    for msg in messages:
        room = room_display_names.get(msg["room_id"], msg["room_id"])
        ts_sec = msg["timestamp"] // 1000
        ts_str = datetime.utcfromtimestamp(ts_sec).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.append(f"\nRoom:    {room}")
        lines.append(f"From:    {msg['sender']}")
        lines.append(f"Time:    {ts_str}")
        lines.append(f"Event:   {msg.get('event_id', '(unknown)')}")
        lines.append(f"Message: {msg['body']}")
        lines.append("-" * 40)
    return "\n".join(lines)


def get_room_display_names(sync_data):
    """Extract human-readable room names from sync data where available."""
    names = {}
    rooms = sync_data.get("rooms", {})
    join = rooms.get("join", {})
    for room_id, room_data in join.items():
        state = room_data.get("state", {}).get("events", [])
        for event in state:
            if event.get("type") == "m.room.name":
                name = event.get("content", {}).get("name", "")
                if name:
                    names[room_id] = name
                    break
    return names


def build_subject(messages, room_display_names):
    senders = list(dict.fromkeys(m["sender"] for m in messages))
    rooms = list(dict.fromkeys(
        room_display_names.get(m["room_id"], m["room_id"]) for m in messages
    ))

    sender_part = senders[0] if len(senders) == 1 else f"{len(senders)} senders"
    room_part = rooms[0] if len(rooms) == 1 else f"{len(rooms)} rooms"

    count = len(messages)
    plural = "s" if count != 1 else ""
    return f"Matrix: {count} new message{plural} from {sender_part} in {room_part}"


def main():
    log("matrix_notify.py starting")

    # Load credentials
    try:
        creds = load_credentials()
    except Exception as e:
        log(f"ERROR loading credentials: {e}")
        sys.exit(1)

    homeserver = creds["homeserver"]
    access_token = creds["access_token"]

    # Read last sync token
    since = read_sync_token()
    if since:
        log(f"Resuming from sync token: {since[:20]}...")
    else:
        log("No prior sync token — first run, will save token and exit")

    # Call Matrix /sync
    try:
        sync_data = matrix_sync(homeserver, access_token, since=since)
    except urllib.error.HTTPError as e:
        log(f"ERROR: Matrix /sync HTTP {e.code}: {e.reason}")
        sys.exit(1)
    except Exception as e:
        log(f"ERROR: Matrix /sync failed: {e}")
        sys.exit(1)

    # Save new sync token
    new_token = sync_data.get("next_batch")
    if new_token:
        write_sync_token(new_token)
        log(f"Saved new sync token: {new_token[:20]}...")
    else:
        log("WARNING: No next_batch token in sync response")

    # On first run there's no prior token; nothing meaningful to check
    if not since:
        log("First run complete — sync token saved, no messages to process")
        return

    # Collect new messages from other users
    messages = collect_new_messages(sync_data)
    log(f"Found {len(messages)} new message(s) from other users")

    if not messages:
        log("No new messages — nothing to do")
        return

    # Build and send notification email
    room_names = get_room_display_names(sync_data)
    subject = build_subject(messages, room_names)
    body = format_email_body(messages, room_names)

    log(f"Sending email: {subject}")
    try:
        result = send_email(
            to=NOTIFY_EMAIL,
            subject=subject,
            body=body,
        )
        log(f"Email sent: {result}")
    except Exception as e:
        log(f"ERROR sending email: {e}")
        sys.exit(1)

    log("matrix_notify.py done")


if __name__ == "__main__":
    main()
