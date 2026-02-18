#!/usr/bin/env python3
"""Test script to verify email threading headers are working correctly."""

import json

def test_reply_headers():
    """Test that reply headers are properly constructed."""

    # Simulate the logic from send_email
    in_reply_to = "<original-message-123@example.com>"
    references = None

    # Test case 1: in_reply_to provided, references not provided
    headers_list = []
    if in_reply_to:
        headers_list.append({"Name": "In-Reply-To", "Value": in_reply_to})
        if not references:
            references = in_reply_to
    if references:
        headers_list.append({"Name": "References", "Value": references})

    print("Test 1 - Single reply:")
    print(json.dumps(headers_list, indent=2))
    assert len(headers_list) == 2
    assert headers_list[0]["Value"] == in_reply_to
    assert headers_list[1]["Value"] == in_reply_to
    print("✓ PASS\n")

    # Test case 2: both in_reply_to and references provided
    in_reply_to = "<reply-message-456@example.com>"
    references = "<original-message-123@example.com> <reply-message-456@example.com>"

    headers_list = []
    if in_reply_to:
        headers_list.append({"Name": "In-Reply-To", "Value": in_reply_to})
        # Only set references from in_reply_to if not already provided
        if not references:
            references = in_reply_to
    if references:
        headers_list.append({"Name": "References", "Value": references})

    print("Test 2 - Multi-message thread:")
    print(json.dumps(headers_list, indent=2))
    assert len(headers_list) == 2
    assert headers_list[0]["Value"] == "<reply-message-456@example.com>"
    assert headers_list[1]["Value"] == "<original-message-123@example.com> <reply-message-456@example.com>"
    print("✓ PASS\n")

    # Test case 3: No reply headers
    in_reply_to = None
    references = None

    headers_list = []
    if in_reply_to or references:
        if in_reply_to:
            headers_list.append({"Name": "In-Reply-To", "Value": in_reply_to})
            if not references:
                references = in_reply_to
        if references:
            headers_list.append({"Name": "References", "Value": references})

    print("Test 3 - New conversation (no reply headers):")
    print(f"Headers list: {headers_list}")
    assert len(headers_list) == 0
    print("✓ PASS\n")

    print("All tests passed!")

if __name__ == "__main__":
    test_reply_headers()
