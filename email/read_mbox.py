#!/usr/bin/env python3
"""Standalone mbox reader that outputs JSON.

Designed to be run via sudo when reading root-owned mailboxes:
    sudo python3 read_mbox.py /var/mail/root

Outputs a JSON array of message objects to stdout.
"""

import email
import email.policy
import json
import mailbox
import sys


def extract_body(msg):
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        # Fallback: try first text part
        for part in msg.walk():
            if part.get_content_type().startswith("text/"):
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
        return ""


def read_mbox_file(path):
    """Read an mbox file and return list of message dicts."""
    try:
        mbox = mailbox.mbox(path)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)

    messages = []
    for msg in mbox:
        message_id = msg.get("Message-ID", "").strip()
        messages.append({
            "message_id": message_id,
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", "(no subject)"),
            "date": msg.get("Date", ""),
            "body": extract_body(msg),
        })

    mbox.close()
    return messages


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <mbox_path>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    messages = read_mbox_file(path)
    json.dump(messages, sys.stdout, ensure_ascii=False)
