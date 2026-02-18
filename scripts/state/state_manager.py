#!/usr/bin/env python3
"""
State Manager - Utilities for managing state.json

This module provides utilities for loading, saving, and managing the state.json file
that tracks Iris's session state, active tasks, personality notes, and recent context.

State persistence allows Iris to maintain continuity across restart cycles:
- Remember what it was working on
- Track progress on multi-step tasks
- Maintain personality and self-notes
- Resume context after crashes or voluntary exits

Usage:
    from state_manager import load_state, save_state, initialize_state

    # Load existing state or get empty dict
    state = load_state()

    # Modify state
    state['session']['last_run'] = datetime.now().isoformat()

    # Save atomically
    save_state(state)
"""

import json
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional


def _db_log_error(summary: str, details: str = None) -> None:
    """Log an error to iris.db activity_log. Silent on failure — avoids circular issues."""
    try:
        from db import log_activity
        log_activity(category='error', summary=summary, details=details)
    except Exception:
        pass


def get_state_schema() -> Dict[str, Any]:
    """
    Return the expected state.json schema/structure.

    This defines the canonical structure for state.json. Any component reading
    or writing state should follow this schema.

    Returns:
        Dictionary with expected state structure and default values
    """
    return {
        "schema_version": "1.0",
        "last_updated": None,

        "session": {
            "last_run": None,  # ISO timestamp of last controller start
            "session_count": 0,  # Total number of times controller has started
            "exit_reason": None,  # Last exit reason: "voluntary", "crash", "kill", "unknown"
            "current_cycle_start": None,  # ISO timestamp of current session start
            "uptime_seconds": 0,  # Approximate uptime before last exit
            "startup_notes": []  # Explicit instructions for next startup (cleared after reading)
        },

        "active_tasks": {
            "current_task": None,  # Description of current task or None
            "task_id": None,  # Database task ID if applicable
            "progress": None,  # Brief progress note
            "checkpoints": [],  # List of checkpoint strings for resumability
            "spawned_workers": []  # List of active worker task IDs
        },

        "personality": {
            "name": "Iris",
            "self_notes": [],  # Things Iris wants to remember about itself
            "preferences": {},  # Learned preferences (e.g., reply style)
            "interaction_count": 0  # Total emails processed
        },

        "recent_context": {
            "last_email": None,  # Brief note about last email processed
            "last_email_timestamp": None,  # ISO timestamp
            "recent_activity": [],  # Last 5-10 activity summaries
            "pending_items": []  # Things to check on next startup
        },

        "system": {
            "total_cycles": 0,  # Total controller restarts (matches session_count)
            "tasks_completed": 0,  # Total tasks completed across all sessions
            "emails_sent": 0,  # Total emails sent
            "workers_spawned": 0,  # Total worker subagents spawned
            "voluntary_exits": 0,  # Count of clean exits vs crashes
            "context_refreshes": 0  # Times controller exited for context cleanup
        }
    }


def initialize_state() -> Dict[str, Any]:
    """
    Create initial state with default values.

    Returns:
        Fresh state dictionary with defaults from schema
    """
    state = get_state_schema()
    state["last_updated"] = datetime.now().isoformat()
    state["session"]["last_run"] = datetime.now().isoformat()
    state["session"]["current_cycle_start"] = datetime.now().isoformat()
    return state


def load_state(state_file: str = '/var/lib/ai-assistant/state.json') -> Dict[str, Any]:
    """
    Load state from JSON file. Return empty dict if not exists.

    This function is designed to be resilient:
    - If file doesn't exist, returns empty dict (not an error)
    - If file is corrupted, logs error and returns empty dict
    - If file is valid but missing keys, returns partial state

    Args:
        state_file: Path to state.json file
                   Development: /home/claude/iris/state.json
                   Production: /var/lib/ai-assistant/state.json

    Returns:
        Dictionary with state data, or empty dict if file doesn't exist
    """
    # If file doesn't exist, return empty dict (not an error - first run)
    if not os.path.exists(state_file):
        return {}

    try:
        with open(state_file, 'r') as f:
            state = json.load(f)
        return state

    except json.JSONDecodeError as e:
        # Corrupted JSON - log error and return empty dict
        print(f"ERROR: Corrupted state.json: {e}")
        print(f"       File: {state_file}")
        print(f"       Returning empty dict. Previous state lost.")
        _db_log_error(
            summary='state.json corrupted (JSON decode error)',
            details=f'File: {state_file} | Error: {e}',
        )
        return {}

    except Exception as e:
        # Other error (permissions, etc)
        print(f"ERROR: Failed to load state.json: {e}")
        print(f"       File: {state_file}")
        print(f"       Returning empty dict.")
        _db_log_error(
            summary=f'state.json load failed: {type(e).__name__}',
            details=f'File: {state_file} | Error: {e}',
        )
        return {}


def save_state(state: Dict[str, Any], state_file: str = '/var/lib/ai-assistant/state.json') -> bool:
    """
    Save state to JSON file atomically (temp file + rename).

    Atomic write prevents corruption if process crashes during write:
    1. Write to temporary file in same directory
    2. Flush and sync to disk
    3. Atomic rename over existing file

    Args:
        state: Dictionary to save as JSON
        state_file: Path to state.json file

    Returns:
        True if save successful, False otherwise
    """
    try:
        # Update timestamp
        state["last_updated"] = datetime.now().isoformat()

        # Create parent directory if it doesn't exist
        state_dir = os.path.dirname(state_file)
        if state_dir and not os.path.exists(state_dir):
            os.makedirs(state_dir, mode=0o755, exist_ok=True)

        # Write to temporary file in same directory (ensures same filesystem)
        fd, temp_path = tempfile.mkstemp(
            dir=state_dir if state_dir else '.',
            prefix='.state-',
            suffix='.json.tmp'
        )

        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk

        # Atomic rename (overwrites existing file atomically)
        os.rename(temp_path, state_file)

        return True

    except Exception as e:
        print(f"ERROR: Failed to save state.json: {e}")
        print(f"       File: {state_file}")

        # Clean up temp file if it exists
        try:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass

        return False


def merge_state(existing: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge updates into existing state, preserving structure.

    This is useful for partial updates where you want to update specific fields
    without overwriting the entire state.

    Args:
        existing: Current state dictionary
        updates: Dictionary with fields to update

    Returns:
        Merged state dictionary
    """
    merged = existing.copy()

    # Deep merge for nested dicts
    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value

    return merged


if __name__ == '__main__':
    # Demo usage
    print("State Manager - Demo")
    print("=" * 60)

    # Show schema
    print("\nExpected state.json schema:")
    schema = get_state_schema()
    print(json.dumps(schema, indent=2))

    # Initialize and save demo state
    demo_state_file = '/tmp/demo_state.json'

    print(f"\nInitializing demo state...")
    state = initialize_state()

    print(f"\nSaving to {demo_state_file}...")
    if save_state(state, demo_state_file):
        print("✓ Save successful")

    print(f"\nLoading from {demo_state_file}...")
    loaded = load_state(demo_state_file)
    print(f"✓ Loaded {len(loaded)} top-level keys")

    print(f"\nDemo complete. State file: {demo_state_file}")
