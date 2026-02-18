#!/usr/bin/env python3
"""
Email sending wrapper that properly loads POSTMARK_API_TOKEN.

The mail-mcp server.py loads POSTMARK_API_TOKEN at module import time,
so we need to set the env var BEFORE importing the module.
"""

import os
import sys

# Load POSTMARK_API_TOKEN from credentials file
POSTMARK_CREDENTIALS = '/home/claude/iris/docs/services/postmark-account.sh'

# Source the credentials by reading and parsing the shell script
if os.path.exists(POSTMARK_CREDENTIALS):
    with open(POSTMARK_CREDENTIALS, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('export POSTMARK_API_TOKEN='):
                # Extract the token value
                token = line.split('=', 1)[1].strip().strip('"').strip("'")
                os.environ['POSTMARK_API_TOKEN'] = token
                break

# NOW import the mail server (it will pick up the env var)
sys.path.append('/home/claude/iris/mail-mcp')
from server import send_email, check_new_emails, read_email, list_emails, update_email_action

# Export the functions for use by other scripts
__all__ = ['send_email', 'check_new_emails', 'read_email', 'list_emails', 'update_email_action']

if __name__ == '__main__':
    # Test that it works
    print(f"✓ POSTMARK_API_TOKEN loaded: {os.environ.get('POSTMARK_API_TOKEN', '')[:8]}...")
    print("✓ Email functions imported successfully")
    print("\nAvailable functions:")
    print("  - send_email(to, subject, body, from_addr=None, cc=None, in_reply_to=None)")
    print("  - check_new_emails(auto_sync=True)")
    print("  - read_email(email_id)")
    print("  - list_emails(limit=10)")
    print("  - update_email_action(email_id, action_todo=None, action_taken=None)")
