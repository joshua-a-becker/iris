#!/usr/bin/env python3
"""
send_matrix_message.py — utility for sending Matrix messages from Iris.

Supports plain messages and threaded replies.
Uses only stdlib (urllib); no external dependencies.

Threading protocol (per Joshua's instructions):
- Top-level message → start a new thread from it
- Message already in a thread → reply within that existing thread
Use smart_reply() to handle this automatically.
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error

CREDENTIALS_FILE = "/home/claude/.config/iris/matrix_credentials.json"


def _load_creds():
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)


def get_event(room_id, event_id):
    """
    Fetch a Matrix event by ID.
    Returns the event dict, or None if not found.
    """
    creds = _load_creds()
    homeserver = creds["homeserver"]
    access_token = creds["access_token"]

    room_id_enc = urllib.parse.quote(room_id)
    event_id_enc = urllib.parse.quote(event_id)
    url = f"{homeserver}/_matrix/client/v3/rooms/{room_id_enc}/event/{event_id_enc}"

    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError:
        return None


def get_thread_root(room_id, event_id):
    """
    Given an event ID, return the thread root event ID.
    If the event is already a thread root, returns event_id.
    If the event is a thread reply, returns the thread root.
    If the event is a plain reply (m.in_reply_to only), returns None (not in a thread).
    """
    event = get_event(room_id, event_id)
    if not event:
        return None

    content = event.get("content", {})
    relates_to = content.get("m.relates_to", {})

    rel_type = relates_to.get("rel_type")
    if rel_type == "m.thread":
        # This event is in a thread — return the thread root
        return relates_to.get("event_id")

    # Not in a thread — this is a top-level or plain-reply event
    return None


def send_message(
    room_id,
    body,
    thread_event_id=None,
    reply_to_event_id=None,
    formatted_body=None,
):
    """
    Send a Matrix message to a room.

    Args:
        room_id:          Full Matrix room ID, e.g. "!abc:server.com"
        body:             Plain-text message body.
        thread_event_id:  Event ID of the thread root. If provided, the message
                          is posted inside that thread.
        reply_to_event_id: Event ID being replied to within the thread (usually
                            the most recent message). Defaults to thread_event_id
                            when threading.
        formatted_body:   Optional HTML-formatted body (m.text format).

    Returns:
        dict with the server response (contains "event_id" on success).
    """
    creds = _load_creds()
    homeserver = creds["homeserver"]
    access_token = creds["access_token"]

    room_id_enc = urllib.parse.quote(room_id)
    txn_id = f"iris_{int(time.time() * 1000)}"
    url = f"{homeserver}/_matrix/client/v3/rooms/{room_id_enc}/send/m.room.message/{txn_id}"

    content = {
        "msgtype": "m.text",
        "body": body,
    }

    if formatted_body:
        content["format"] = "org.matrix.custom.html"
        content["formatted_body"] = formatted_body

    if thread_event_id:
        in_reply_to = reply_to_event_id if reply_to_event_id else thread_event_id
        content["m.relates_to"] = {
            "rel_type": "m.thread",
            "event_id": thread_event_id,
            "m.in_reply_to": {
                "event_id": in_reply_to,
            },
            "is_falling_back": False,
        }
    elif reply_to_event_id:
        # Plain reply (no thread)
        content["m.relates_to"] = {
            "m.in_reply_to": {
                "event_id": reply_to_event_id,
            }
        }

    data = json.dumps(content).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="PUT",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def smart_reply(room_id, body, reply_to_event_id, formatted_body=None):
    """
    Reply to a Matrix message, automatically handling threading:
    - If the target event is in a thread, reply within that thread.
    - If the target event is a top-level message, start a new thread from it.

    This is the recommended way to reply to any Matrix message.
    """
    thread_root = get_thread_root(room_id, reply_to_event_id)

    if thread_root:
        # Already in a thread — reply within it
        return send_message(
            room_id, body,
            thread_event_id=thread_root,
            reply_to_event_id=reply_to_event_id,
            formatted_body=formatted_body
        )
    else:
        # Top-level message — start a new thread
        return send_message(
            room_id, body,
            thread_event_id=reply_to_event_id,
            reply_to_event_id=reply_to_event_id,
            formatted_body=formatted_body
        )


def send_plain(room_id, body):
    """Convenience wrapper: send a plain (non-threaded) message."""
    return send_message(room_id, body)


def send_threaded(room_id, body, thread_root_id, reply_to_id=None):
    """Convenience wrapper: send a message inside an existing thread."""
    return send_message(
        room_id,
        body,
        thread_event_id=thread_root_id,
        reply_to_event_id=reply_to_id or thread_root_id,
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: send_matrix_message.py <room_id> <message> [reply_to_event_id]")
        sys.exit(1)

    _room_id = sys.argv[1]
    _body = sys.argv[2]
    _reply_to = sys.argv[3] if len(sys.argv) > 3 else None

    if _reply_to:
        result = smart_reply(_room_id, _body, _reply_to)
    else:
        result = send_plain(_room_id, _body)

    print(f"Sent: {result.get('event_id')}")
