# Email Threading Examples

This document shows how to use the enhanced `send_email()` function with explicit threading control.

## Overview

The `send_email()` function now requires explicit declaration of threading intent via the `is_reply` parameter:

- **New threads**: `is_reply=False` (default) - no threading headers
- **Replies**: `is_reply=True` - requires `in_reply_to`, auto-populates `references`

## Example 1: Sending a New Thread

```python
from server import send_email

# Start a new conversation
send_email(
    to="alice@example.com",
    subject="Project Update",
    body="Hi Alice,\n\nHere's the latest update...",
    is_reply=False  # Explicit: this is a new thread
)
```

## Example 2: Replying to an Email

```python
from server import send_email, read_email

# Read an email and extract Message-ID
email_content = read_email("abc123def456")  # Use the email hash ID

# Extract Message-ID (it's in the first line of the content)
message_id = None
for line in email_content.split('\n'):
    if line.startswith('Message-ID:'):
        message_id = line.split(':', 1)[1].strip()
        break

# Send a threaded reply
send_email(
    to="alice@example.com",
    subject="Re: Project Update",
    body="Hi Alice,\n\nThanks for your message...",
    is_reply=True,  # Explicit: this is a reply
    in_reply_to=message_id  # Required when is_reply=True
    # references auto-populated from in_reply_to if omitted
)
```

## Example 3: Replying with Full Thread Context

```python
# For long threads, you may want to provide full references
email_content = read_email("abc123def456")

# Extract both Message-ID and References
message_id = None
references = None
for line in email_content.split('\n'):
    if line.startswith('Message-ID:'):
        message_id = line.split(':', 1)[1].strip()
    elif line.startswith('References:'):
        references = line.split(':', 1)[1].strip()

# Build full reference chain
full_references = f"{references} {message_id}" if references else message_id

send_email(
    to="alice@example.com",
    subject="Re: Project Update",
    body="Continuing the discussion...",
    is_reply=True,
    in_reply_to=message_id,
    references=full_references  # Full thread history
)
```

## What Will Fail

### ❌ New thread with threading headers

```python
# This will raise ValueError
send_email(
    to="alice@example.com",
    subject="Project Update",
    body="...",
    is_reply=False,
    in_reply_to="<some-id@example.com>"  # ERROR: conflicting intent
)
```

### ❌ Reply without in_reply_to

```python
# This will raise ValueError
send_email(
    to="alice@example.com",
    subject="Re: Project Update",
    body="...",
    is_reply=True  # ERROR: is_reply=True requires in_reply_to
)
```

## Benefits

1. **Explicit intent**: Impossible to accidentally send unthreaded replies
2. **Auto-population**: `references` automatically populated from `in_reply_to` if omitted
3. **Compile-time safety**: IDEs can show parameter requirements
4. **Runtime validation**: Helpful error messages if you get it wrong

## Migration Notes

Existing code that sends **new threads** will continue to work (is_reply defaults to False).

Existing code that sends **replies** needs to be updated to:
1. Add `is_reply=True`
2. Ensure `in_reply_to` is provided
3. Optionally remove `references` (it will be auto-populated)
