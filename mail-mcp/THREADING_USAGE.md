# Email Threading Usage Guide

## Overview

The `send_email()` function now supports proper email threading through `In-Reply-To` and `References` headers. This ensures replies appear in the correct conversation thread in email clients instead of starting new conversations.

## Updated Function Signature

```python
send_email(
    to: str,
    subject: str,
    body: str,
    from_addr: str = DEFAULT_FROM,
    in_reply_to: str = None,     # NEW
    references: str = None        # NEW
)
```

## Parameters

- **in_reply_to**: Message-ID of the email being replied to (e.g., `<abc123@example.com>`)
- **references**: Space-separated chain of Message-IDs in the conversation thread

## Usage Examples

### Example 1: Simple Reply

When replying to a single email:

```python
# Original email has Message-ID: <original-123@example.com>

send_email(
    to="user@example.com",
    subject="Re: Your question",
    body="Here's the answer...",
    in_reply_to="<original-123@example.com>"
)
```

**Result**: The `References` header will automatically be set to the same value as `In-Reply-To`.

### Example 2: Multi-Message Thread

When replying in a conversation with multiple messages:

```python
# Thread has 3 messages:
# 1. <msg-1@example.com>
# 2. <msg-2@example.com>
# 3. <msg-3@example.com> (the one you're replying to)

send_email(
    to="user@example.com",
    subject="Re: Discussion topic",
    body="Continuing the conversation...",
    in_reply_to="<msg-3@example.com>",
    references="<msg-1@example.com> <msg-2@example.com> <msg-3@example.com>"
)
```

### Example 3: New Conversation

When starting a new conversation (no threading needed):

```python
send_email(
    to="user@example.com",
    subject="New topic",
    body="Let's discuss something new..."
)
```

**Result**: No reply headers are added. This starts a fresh conversation.

## Workflow: Reading and Replying

### Step 1: Read an Email

Use `read_email()` to get the full email content including Message-ID:

```python
content = read_email("abc123def456")
```

The output will include:
```
Message-ID: <original-message@example.com>
In-Reply-To: <previous-message@example.com>  # if present
References: <msg-1@ex.com> <msg-2@ex.com>   # if present
Date: Mon, 15 Feb 2026 10:30:00 +0000
From: sender@example.com
...
```

### Step 2: Extract Message-ID

Parse the Message-ID from the output (typically the first line).

### Step 3: Send Reply with Threading

```python
send_email(
    to="sender@example.com",
    subject="Re: Original Subject",
    body="Your reply here...",
    in_reply_to="<original-message@example.com>",
    references="<previous-message@example.com> <original-message@example.com>"
)
```

## Implementation Details

### Postmark API

Headers are sent via the `Headers` array in the API payload:

```json
{
  "From": "iris@[YOUR_DOMAIN]",
  "To": "recipient@example.com",
  "Subject": "Re: Topic",
  "TextBody": "Message body",
  "Headers": [
    {"Name": "In-Reply-To", "Value": "<msg-id@example.com>"},
    {"Name": "References", "Value": "<msg-id@example.com>"}
  ]
}
```

### Sendmail Fallback

Headers are included in the raw email message:

```
From: iris@[YOUR_DOMAIN]
To: recipient@example.com
Subject: Re: Topic
Date: Mon, 15 Feb 2026 10:30:00 +0000
Message-ID: <mcp-1739610600@example.com>
In-Reply-To: <msg-id@example.com>
References: <msg-id@example.com>
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8

Message body
```

## Automatic Reference Building

If you provide `in_reply_to` but not `references`, the function automatically uses `in_reply_to` as the `references` value. This handles the common case of replying to a single message.

```python
# These are equivalent:
send_email(..., in_reply_to="<msg@ex.com>")
send_email(..., in_reply_to="<msg@ex.com>", references="<msg@ex.com>")
```

## Email Index

The email index now stores `in_reply_to` and `references` for all synced emails, making it easier to build proper reply chains when responding.

## Testing

A test script is available at `/home/claude/mail-mcp/test_threading.py` to verify the header logic.

Run it with:
```bash
python3 /home/claude/mail-mcp/test_threading.py
```
