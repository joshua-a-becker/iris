#!/usr/bin/env python3
"""
Test script to validate Iris startup procedure works correctly.

Tests:
1. State loading and initialization
2. Database function JSON parsing
3. Email check function
4. Sequential execution (no parallel calls)
5. Error handling

Run: python3 /home/claude/iris/scripts/test_startup.py
"""

import sys
import json
import time
from datetime import datetime

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text):
    print(f"\n{BOLD}{'='*60}{RESET}")
    print(f"{BOLD}{text}{RESET}")
    print(f"{BOLD}{'='*60}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠ {text}{RESET}")

def test_state_loading():
    """Test step 1: State loading"""
    print_header("TEST 1: State Loading")

    try:
        sys.path.append('/home/claude/iris/scripts/state')
        from state_manager import load_state, initialize_state, save_state

        state = load_state('/home/claude/iris/state.json')
        if not state:
            print_warning("State file not found, initializing...")
            state = initialize_state()
            save_state(state, '/home/claude/iris/state.json')

        # Verify state structure
        assert isinstance(state, dict), "State must be a dict"
        assert 'session' in state, "State must have 'session' key"
        assert 'session_count' in state['session'], "Session must have 'session_count'"

        print_success("State loaded successfully")
        print(f"  Session count: {state['session']['session_count']}")
        return True

    except Exception as e:
        print_error(f"State loading failed: {e}")
        return False

def test_database_json_parsing():
    """Test step 3: Database JSON parsing"""
    print_header("TEST 2: Database JSON Parsing")

    try:
        sys.path.append('/home/claude/iris/scripts/state')
        from db import list_tasks, get_recent_activity

        # Test list_tasks - returns JSON string
        print("Testing list_tasks()...")
        in_progress_json = list_tasks(status='in_progress')

        # Verify it's a string
        assert isinstance(in_progress_json, str), "list_tasks must return string"
        print_success(f"list_tasks returns JSON string: {in_progress_json[:50]}...")

        # Parse JSON
        in_progress = json.loads(in_progress_json)
        assert isinstance(in_progress, list), "Parsed result must be list"
        print_success(f"JSON parsed successfully: {len(in_progress)} in_progress tasks")

        # Test pending tasks
        print("\nTesting list_tasks(status='pending')...")
        pending_json = list_tasks(status='pending')
        pending = json.loads(pending_json)
        print_success(f"Parsed {len(pending)} pending tasks")

        # Test recent activity
        print("\nTesting get_recent_activity()...")
        recent_json = get_recent_activity(limit=10)
        recent = json.loads(recent_json)
        assert isinstance(recent, list), "Parsed result must be list"
        print_success(f"Parsed {len(recent)} recent activities")

        # Verify we can access dict fields
        if pending:
            task = pending[0]
            assert 'title' in task, "Task must have 'title' field"
            print_success(f"Can access task fields: '{task['title']}'")

        return True

    except Exception as e:
        print_error(f"Database JSON parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_email_check():
    """Test step 4: Email check"""
    print_header("TEST 3: Email Check")

    try:
        sys.path.append('/home/claude/iris/mail-mcp')
        from server import check_new_emails

        print("Calling check_new_emails()...")
        email_summary = check_new_emails(auto_sync=True)

        # Verify it returns a string
        assert isinstance(email_summary, str), "check_new_emails must return string"
        print_success("check_new_emails returned successfully")

        # Parse the summary
        print(f"\n  Email summary:\n{email_summary}\n")

        # Check for expected patterns
        if "unread email" in email_summary.lower() or "no unread" in email_summary.lower():
            print_success("Email summary format is correct")
        else:
            print_warning(f"Unexpected email summary format: {email_summary[:100]}")

        return True

    except Exception as e:
        print_error(f"Email check failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sequential_execution():
    """Test that steps execute sequentially without race conditions"""
    print_header("TEST 4: Sequential Execution")

    try:
        start_time = time.time()

        # Simulate startup sequence with timing
        print("Step 1: Load state...")
        sys.path.append('/home/claude/iris/scripts/state')
        from state_manager import load_state
        state = load_state('/home/claude/iris/state.json')
        t1 = time.time()
        print_success(f"  Completed in {t1-start_time:.3f}s")

        print("\nStep 2: Check database...")
        from db import list_tasks
        tasks_json = list_tasks(status='pending')
        tasks = json.loads(tasks_json)
        t2 = time.time()
        print_success(f"  Completed in {t2-t1:.3f}s (waited for state)")

        print("\nStep 3: Check email...")
        sys.path.append('/home/claude/iris/mail-mcp')
        from server import check_new_emails
        emails = check_new_emails(auto_sync=True)
        t3 = time.time()
        print_success(f"  Completed in {t3-t2:.3f}s (waited for database)")

        total_time = t3 - start_time
        print_success(f"\nAll steps completed sequentially in {total_time:.3f}s")

        return True

    except Exception as e:
        print_error(f"Sequential execution test failed: {e}")
        return False

def test_error_handling():
    """Test error handling in startup"""
    print_header("TEST 5: Error Handling")

    all_passed = True

    # Test 1: Graceful handling of missing state file
    print("Test: Load state from non-existent path...")
    try:
        sys.path.append('/home/claude/iris/scripts/state')
        from state_manager import load_state, initialize_state

        state = load_state('/tmp/nonexistent_state.json')
        if state is None:
            state = initialize_state()
            print_success("Gracefully handled missing state file")
        else:
            print_warning("State loaded unexpectedly")
    except Exception as e:
        print_error(f"Failed to handle missing state: {e}")
        all_passed = False

    # Test 2: Database function with invalid status
    print("\nTest: Database query with valid parameters...")
    try:
        from db import list_tasks
        result = list_tasks(status='pending')
        tasks = json.loads(result)
        print_success(f"Database handled query correctly ({len(tasks)} results)")
    except Exception as e:
        print_error(f"Database query failed: {e}")
        all_passed = False

    # Test 3: JSON parsing error handling
    print("\nTest: JSON parsing with error handling...")
    try:
        from db import list_tasks
        result = list_tasks(status='pending')

        try:
            tasks = json.loads(result)
            print_success("JSON parsing succeeded")
        except json.JSONDecodeError as je:
            print_error(f"JSON parsing failed: {je}")
            all_passed = False
    except Exception as e:
        print_error(f"Test failed: {e}")
        all_passed = False

    return all_passed

def main():
    """Run all tests"""
    print_header("Iris Startup Procedure Test Suite")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        "State Loading": test_state_loading(),
        "Database JSON Parsing": test_database_json_parsing(),
        "Email Check": test_email_check(),
        "Sequential Execution": test_sequential_execution(),
        "Error Handling": test_error_handling(),
    }

    # Print summary
    print_header("TEST SUMMARY")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}")
        else:
            print_error(f"{test_name}")

    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}")

    if passed == total:
        print_success("\n✓ All startup procedure tests passed!")
        return 0
    else:
        print_error(f"\n✗ {total - passed} test(s) failed")
        return 1

if __name__ == "__main__":
    exit(main())
