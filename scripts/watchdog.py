#!/usr/bin/env python3
"""
Iris Multi-Condition Monitoring Watchdog

This script monitors for alert conditions and breaks when any trigger:
- New email arrives
- CPU usage exceeds 90%
- Free disk space drops below 10GB

The script is designed to run in a background Bash subagent. When an alert
triggers, the script exits, causing the subagent to complete and send a
<task-notification> to the controller.

Usage:
    python3 -u /home/claude/iris/scripts/watchdog.py

The -u flag is critical for unbuffered output so alerts are visible immediately.
"""

import time
import sys
import psutil
import shutil
import gzip
import os
from pathlib import Path

# Add mail tools to path (using canonical MCP version)
sys.path.append('/home/claude/iris/mail-mcp')
from server import check_new_emails

# Add state path for DB error logging
sys.path.append('/home/claude/iris/scripts/state')


def _db_log_error(summary: str, details: str = None) -> None:
    """Log an error to the iris.db activity_log. Silent on failure — never break watchdog."""
    try:
        from db import log_activity
        log_activity(category='error', summary=summary, details=details)
    except Exception:
        pass  # DB logging must never crash the watchdog

# Disk space threshold (bytes)
DISK_SPACE_THRESHOLD_GB = 10
DISK_SPACE_THRESHOLD_BYTES = DISK_SPACE_THRESHOLD_GB * 1024 * 1024 * 1024

# Iris-controlled directories eligible for cleanup
CLEANUP_ATTACHMENTS_DIR = Path('/home/claude/iris/docs/emails/attachments')
CLEANUP_LOGS_DIR = Path('/home/claude/iris/logs')


def get_free_space_gb() -> float:
    """Return free space on the / partition in GB."""
    usage = shutil.disk_usage('/')
    return usage.free / (1024 ** 3)


def cleanup_attachments() -> int:
    """
    Remove duplicate attachments (files with _N suffix that match the base file).
    Returns number of bytes freed.
    """
    freed = 0
    if not CLEANUP_ATTACHMENTS_DIR.exists():
        return freed

    for email_dir in CLEANUP_ATTACHMENTS_DIR.iterdir():
        if not email_dir.is_dir():
            continue
        # Group files by base name (strip _N suffix)
        import re
        base_map: dict[str, Path] = {}
        duplicates: list[Path] = []

        for f in sorted(email_dir.iterdir()):
            if not f.is_file():
                continue
            # Check if this is a numbered duplicate: name_N.ext
            stem, ext = os.path.splitext(f.name)
            m = re.match(r'^(.+)_(\d+)$', stem)
            if m:
                base_name = m.group(1) + ext
                base_file = email_dir / base_name
                if base_file.exists():
                    # Compare content
                    try:
                        if f.read_bytes() == base_file.read_bytes():
                            duplicates.append(f)
                    except Exception:
                        pass
            else:
                base_map[f.name] = f

        for dup in duplicates:
            try:
                size = dup.stat().st_size
                dup.unlink()
                freed += size
            except Exception:
                pass

    return freed


def cleanup_logs() -> int:
    """
    Compress old log files and trim large ones in /home/claude/iris/logs/.
    Returns number of bytes freed.
    """
    freed = 0
    if not CLEANUP_LOGS_DIR.exists():
        return freed

    MAX_LOG_SIZE = 1 * 1024 * 1024  # 1 MB threshold for compression

    for log_file in CLEANUP_LOGS_DIR.iterdir():
        if not log_file.is_file():
            continue
        # Skip already-compressed files
        if log_file.suffix == '.gz':
            continue
        try:
            size = log_file.stat().st_size
            if size > MAX_LOG_SIZE:
                gz_path = log_file.with_suffix(log_file.suffix + '.gz')
                with open(log_file, 'rb') as f_in:
                    with gzip.open(gz_path, 'wb') as f_out:
                        f_out.write(f_in.read())
                compressed_size = gz_path.stat().st_size
                log_file.unlink()
                freed += size - compressed_size
        except Exception:
            pass

    return freed


def run_disk_cleanup() -> str:
    """Run cleanup on Iris-controlled folders and return a summary string."""
    att_freed = cleanup_attachments()
    log_freed = cleanup_logs()
    total_freed_mb = (att_freed + log_freed) / (1024 ** 2)
    return (
        f"Cleanup: freed {total_freed_mb:.1f} MB total "
        f"(attachments: {att_freed / (1024**2):.1f} MB, "
        f"logs: {log_freed / (1024**2):.1f} MB)"
    )


LOG_FILE = Path('/tmp/iris_watchdog.log')


def log(msg: str) -> None:
    """Write to log file only — never stdout. Subagent sees nothing to act on."""
    import datetime
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f"{datetime.datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass


def main():
    """Main watchdog monitoring loop."""
    log('Watchdog started - monitoring for alerts')
    log('  Checking: email (every 1s), CPU (every 5s), disk (every 60s)')
    log('  Max runtime: 9m50s (clean exit before Task timeout)')

    import datetime
    start_time = datetime.datetime.now()
    max_runtime = datetime.timedelta(seconds=590)  # 9min 50sec - exit before Task timeout

    iteration = 0
    email_check_failures = 0  # consecutive email-check failures
    EMAIL_FAIL_LOG_THRESHOLD = 5  # only DB-log after this many consecutive failures

    while True:
        iteration += 1

        # Touch heartbeat file so external monitor knows watchdog is alive
        try:
            Path('/tmp/iris_watchdog_heartbeat').touch()
        except Exception:
            pass  # Never let heartbeat failure break the watchdog

        # Check if we've exceeded max runtime
        elapsed = datetime.datetime.now() - start_time
        if elapsed >= max_runtime:
            log('Watchdog timeout - 10 minutes elapsed, no alerts')
            log('Watchdog exiting - clean timeout')
            return 0

        # Check for new email (every iteration)
        try:
            result = check_new_emails()
            if email_check_failures > 0:
                email_check_failures = 0  # reset on success
            if 'unread' in result.lower():
                # Find the line with "unread email(s):"
                for line in result.split('\n'):
                    if 'unread email' in line.lower():
                        # Extract the number at the start of this line
                        parts = line.strip().split()
                        if parts and parts[0].isdigit():
                            count = int(parts[0])
                            if count > 0:
                                log(f'ALERT: NEW_EMAIL - {count} unread')
                                break
                else:
                    continue
                break
        except Exception as e:
            log(f'Email check error: {e}')
            email_check_failures += 1
            if email_check_failures == EMAIL_FAIL_LOG_THRESHOLD:
                _db_log_error(
                    summary=f'Watchdog: email check failing repeatedly ({email_check_failures}x)',
                    details=f'Latest error: {e}',
                )

        # Check CPU usage (every 5 iterations = ~5 seconds)
        if iteration % 5 == 0:
            try:
                cpu_percent = psutil.cpu_percent(interval=0.1)
                if cpu_percent > 90:
                    log(f'ALERT: HIGH_CPU - {cpu_percent}% usage')
                    break
            except Exception as e:
                log(f'CPU check error: {e}')

        # Check disk space (every 60 iterations = ~60 seconds)
        if iteration % 60 == 0:
            try:
                free_gb = get_free_space_gb()
                if free_gb < DISK_SPACE_THRESHOLD_GB:
                    log(
                        f'ALERT: DISK_SPACE - only {free_gb:.2f} GB free '
                        f'(threshold: {DISK_SPACE_THRESHOLD_GB} GB)'
                    )
                    # Attempt automated cleanup before alerting controller
                    cleanup_summary = run_disk_cleanup()
                    log(f'  {cleanup_summary}')
                    free_gb_after = get_free_space_gb()
                    log(f'  Free space after cleanup: {free_gb_after:.2f} GB')
                    break
                else:
                    log(f'Disk OK: {free_gb:.2f} GB free')
            except Exception as e:
                log(f'Disk check error: {e}')

        # Sleep before next iteration
        time.sleep(1)

    log('Watchdog exiting - alert triggered')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log('Watchdog interrupted')
        sys.exit(1)
    except Exception as e:
        log(f'Watchdog crashed: {e}')
        _db_log_error(
            summary=f'Watchdog crashed: {type(e).__name__}',
            details=str(e),
        )
        sys.exit(1)
