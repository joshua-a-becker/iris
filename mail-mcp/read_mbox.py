#!/usr/bin/env python3
"""Standalone mbox reader that outputs JSON.

Designed to be run via sudo when reading root-owned mailboxes:
    sudo python3 read_mbox.py /var/mail/root

Outputs a JSON array of message objects to stdout.
"""

import base64
import email
import email.policy
import hashlib
import json
import mailbox
import mimetypes
import os
import sys
from pathlib import Path

ATTACHMENTS_BASE_DIR = Path("/home/claude/iris/docs/emails/attachments")


def extract_body(msg):
    """Extract plain text body from an email message."""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                # Skip parts that are attachments
                if part.get_content_disposition() in ("attachment", "inline") and part.get_filename():
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        # Fallback: try first text part that isn't an attachment
        for part in msg.walk():
            if part.get_content_type().startswith("text/"):
                if part.get_content_disposition() == "attachment":
                    continue
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            return payload.decode("utf-8", errors="replace")
        return ""


def _make_email_hash(message_id: str, from_addr: str, date: str) -> str:
    """Create a short hash for organizing attachment directories."""
    content = f"{message_id}{from_addr}{date}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]


def extract_attachments(msg, email_hash: str) -> list:
    """Extract attachments from a MIME message, save to disk, return metadata list."""
    attachments = []

    if not msg.is_multipart():
        return attachments

    attach_dir = ATTACHMENTS_BASE_DIR / email_hash

    for part in msg.walk():
        content_disposition = part.get_content_disposition()
        filename = part.get_filename()

        # Consider a part an attachment if it has a filename or is explicitly attached
        if not filename and content_disposition != "attachment":
            continue

        # Skip plain text body parts without filenames
        content_type = part.get_content_type()
        if not filename and content_type in ("text/plain", "text/html"):
            continue

        # Get the payload
        payload = part.get_payload(decode=True)
        if payload is None:
            continue

        # Sanitize filename
        if filename:
            # Decode encoded filename if necessary
            try:
                from email.header import decode_header
                decoded_parts = decode_header(filename)
                filename = "".join(
                    part.decode(enc or "utf-8") if isinstance(part, bytes) else part
                    for part, enc in decoded_parts
                )
            except Exception:
                pass
            # Remove path components and sanitize
            filename = os.path.basename(filename)
            filename = "".join(c for c in filename if c.isalnum() or c in "._- ")
            filename = filename.strip() or "attachment"
        else:
            # Generate a filename from content type
            ext = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".bin"
            filename = f"attachment{ext}"

        # Ensure attachment directory exists
        try:
            attach_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            attachments.append({
                "filename": filename,
                "content_type": content_type,
                "size": len(payload),
                "path": None,
                "error": f"Could not create directory: {e}",
            })
            continue

        # If the file already exists with the same content, skip saving (idempotent)
        save_path = attach_dir / filename
        if save_path.exists():
            try:
                existing = save_path.read_bytes()
                if existing == payload:
                    # Already saved correctly - return existing path without duplication
                    attachments.append({
                        "filename": save_path.name,
                        "content_type": content_type,
                        "size": len(payload),
                        "path": str(save_path),
                    })
                    continue
            except Exception:
                pass
            # Different content - find a non-colliding name
            base, ext_part = os.path.splitext(filename)
            counter = 1
            while save_path.exists():
                save_path = attach_dir / f"{base}_{counter}{ext_part}"
                counter += 1

        # Save attachment to disk
        try:
            with open(save_path, "wb") as f:
                f.write(payload)
            attachments.append({
                "filename": save_path.name,
                "content_type": content_type,
                "size": len(payload),
                "path": str(save_path),
            })
        except Exception as e:
            attachments.append({
                "filename": filename,
                "content_type": content_type,
                "size": len(payload),
                "path": None,
                "error": f"Could not save: {e}",
            })

    return attachments


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
        in_reply_to = msg.get("In-Reply-To", "").strip()
        references = msg.get("References", "").strip()
        from_addr = msg.get("From", "")
        date_str = msg.get("Date", "")

        # Compute email hash for attachment directory naming
        email_hash = _make_email_hash(message_id, from_addr, date_str)

        # Extract attachments if multipart
        attachments = extract_attachments(msg, email_hash)

        messages.append({
            "message_id": message_id,
            "from": from_addr,
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", "(no subject)"),
            "date": date_str,
            "body": extract_body(msg),
            "in_reply_to": in_reply_to,
            "references": references,
            "attachments": attachments,
            "email_hash": email_hash,
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
