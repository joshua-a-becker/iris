#!/usr/bin/env python3
"""
Watchdog Keeper - Ensures email watchdog is always running

This script runs continuously and checks every 30 seconds whether
the watchdog.py process is running. If not, it restarts it.

This solves the problem where the watchdog exits on email alert
but doesn't get restarted.
"""

import subprocess
import time
import sys
from datetime import datetime

WATCHDOG_SCRIPT = "/home/claude/iris/scripts/watchdog.py"
CHECK_INTERVAL = 30  # seconds

def is_watchdog_running():
    """Check if watchdog.py is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "watchdog.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0  # 0 = process found
    except Exception as e:
        print(f"Error checking watchdog: {e}", file=sys.stderr)
        return False

def start_watchdog():
    """Start the watchdog script in the background."""
    try:
        # Start watchdog with environment variables passed through
        env = subprocess.os.environ.copy()

        subprocess.Popen(
            ["python3", "-u", WATCHDOG_SCRIPT],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True  # Detach from parent
        )

        print(f"[{datetime.now().isoformat()}] ✓ Watchdog started", flush=True)
        return True
    except Exception as e:
        print(f"[{datetime.now().isoformat()}] ✗ Failed to start watchdog: {e}", file=sys.stderr, flush=True)
        return False

def main():
    """Main loop - check and restart watchdog as needed."""
    print(f"[{datetime.now().isoformat()}] Watchdog Keeper starting...", flush=True)
    print(f"  Checking every {CHECK_INTERVAL}s", flush=True)
    print(f"  Watchdog script: {WATCHDOG_SCRIPT}", flush=True)

    # Ensure watchdog is running at startup
    if not is_watchdog_running():
        print(f"[{datetime.now().isoformat()}] Watchdog not running at startup, starting now...", flush=True)
        start_watchdog()
        time.sleep(2)  # Give it time to start
    else:
        print(f"[{datetime.now().isoformat()}] Watchdog already running", flush=True)

    # Main monitoring loop
    while True:
        time.sleep(CHECK_INTERVAL)

        if not is_watchdog_running():
            print(f"[{datetime.now().isoformat()}] ⚠️  Watchdog stopped! Restarting...", flush=True)
            start_watchdog()
        else:
            print(f"[{datetime.now().isoformat()}] ✓ Watchdog healthy", flush=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{datetime.now().isoformat()}] Watchdog Keeper stopped by user", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"\n[{datetime.now().isoformat()}] FATAL ERROR: {e}", file=sys.stderr, flush=True)
        sys.exit(1)
