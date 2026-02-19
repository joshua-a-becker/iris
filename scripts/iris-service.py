#!/usr/bin/env python3
"""
Iris Service Wrapper
Manages Claude Code CLI as a long-lived daemon for email agent operations.

This script is designed to be run by systemd as a simple service.
It spawns Claude Code CLI as a subprocess, feeds it the session restart
prompt, monitors health, and handles graceful shutdown.

Design doc: /home/claude/scripts/SYSTEMD_SERVICE_DESIGN.md
"""

import os
import sys
import time
import signal
import subprocess
import logging
import threading
from pathlib import Path
from datetime import datetime, timezone

# =============================================================================
# Configuration
# =============================================================================

HOME = Path("/home/claude")
DB_PATH = HOME / "iris" / "memory-legacy" / "iris.db"
DB_MODULE = HOME / "iris" / "memory-legacy" / "db.py"
MASTER_LOG = HOME / "iris-v1-archive" / "master_log.md"
SERVICE_LOG = HOME / "iris" / "logs-service" / "iris-service.log"
CLAUDE_BIN = HOME / ".local" / "bin" / "claude"
MAIL_MCP_SERVER = HOME / "iris" / "mail-mcp" / "server.py"
CREDENTIALS_FILE = HOME / ".config" / "moltbook" / "credentials.json"
EXISTENTIAL_INSTRUCTIONS = HOME / "existential-instructions.md"

# Restart backoff configuration
INITIAL_RESTART_DELAY = 10   # seconds
MAX_RESTART_DELAY = 300      # 5 minutes max
BACKOFF_FACTOR = 2
MAX_RESTART_ATTEMPTS = 10    # per service invocation (systemd also limits)

# =============================================================================
# Logging setup
# =============================================================================

# Ensure logs directory exists
SERVICE_LOG.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),        # Goes to journald
        logging.FileHandler(SERVICE_LOG, mode='a') # Archival
    ]
)
logger = logging.getLogger('iris-service')

# =============================================================================
# Global state
# =============================================================================

claude_process = None
shutdown_requested = False


# =============================================================================
# Pre-flight checks
# =============================================================================

def pre_flight_checks():
    """Validate environment before starting Claude Code. Returns True if OK."""
    logger.info("Running pre-flight checks...")
    all_ok = True

    # Check database
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        all_ok = False
    else:
        # Verify DB is readable
        try:
            import sqlite3
            conn = sqlite3.connect(str(DB_PATH))
            conn.execute("SELECT COUNT(*) FROM tasks")
            conn.close()
            logger.info(f"  Database OK: {DB_PATH}")
        except Exception as e:
            logger.error(f"  Database read failed: {e}")
            all_ok = False

    # Check Claude Code CLI
    if not CLAUDE_BIN.exists():
        logger.error(f"Claude Code CLI not found: {CLAUDE_BIN}")
        all_ok = False
    else:
        logger.info(f"  Claude CLI OK: {CLAUDE_BIN}")

    # Check mail MCP server
    if not MAIL_MCP_SERVER.exists():
        logger.error(f"Mail MCP server not found: {MAIL_MCP_SERVER}")
        all_ok = False
    else:
        logger.info(f"  Mail MCP server OK: {MAIL_MCP_SERVER}")

    # Check credentials (non-fatal warning)
    if not CREDENTIALS_FILE.exists():
        logger.warning(f"  Moltbook credentials not found: {CREDENTIALS_FILE} (non-fatal)")
    else:
        logger.info(f"  Moltbook credentials OK: {CREDENTIALS_FILE}")

    # Check existential instructions
    if not EXISTENTIAL_INSTRUCTIONS.exists():
        logger.error(f"Existential instructions not found: {EXISTENTIAL_INSTRUCTIONS}")
        all_ok = False
    else:
        logger.info(f"  Existential instructions OK: {EXISTENTIAL_INSTRUCTIONS}")

    if all_ok:
        logger.info("Pre-flight checks PASSED.")
    else:
        logger.error("Pre-flight checks FAILED.")

    return all_ok


# =============================================================================
# State management
# =============================================================================

def log_session_start():
    """Log service start to master log and database."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Append to master log (prepend to top)
    try:
        entry = f"### {timestamp} — Service started (systemd)\n\n"
        entry += "Iris service wrapper started via systemd. Spawning Claude Code CLI.\n\n"

        if MASTER_LOG.exists():
            content = MASTER_LOG.read_text()
            MASTER_LOG.write_text(entry + content)
        else:
            MASTER_LOG.write_text(entry)

        logger.info("Logged session start to master_log.md")
    except Exception as e:
        logger.error(f"Failed to update master log: {e}")

    # Log to database via db module
    try:
        result = subprocess.run(
            [
                sys.executable, "-c",
                "import sys; sys.path.insert(0, '/home/claude/iris/memory-legacy'); "
                "from db import log_activity; "
                "print(log_activity('session', 'Service started via systemd', "
                "'Iris systemd service wrapper launched Claude Code CLI'))"
            ],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            logger.info(f"Logged session start to database: {result.stdout.strip()}")
        else:
            logger.error(f"Database logging failed: {result.stderr.strip()}")
    except Exception as e:
        logger.error(f"Database logging exception: {e}")


def log_session_end(reason="shutdown"):
    """Log service stop to master log and database."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    try:
        entry = f"### {timestamp} — Service stopped ({reason})\n\n"
        if MASTER_LOG.exists():
            content = MASTER_LOG.read_text()
            MASTER_LOG.write_text(entry + content)
        logger.info("Logged session end to master_log.md")
    except Exception as e:
        logger.error(f"Failed to update master log on shutdown: {e}")

    try:
        subprocess.run(
            [
                sys.executable, "-c",
                "import sys; sys.path.insert(0, '/home/claude/iris/memory-legacy'); "
                "from db import log_activity; "
                f"log_activity('session', 'Service stopped: {reason}', "
                f"'Iris systemd service wrapper shutting down: {reason}')"
            ],
            capture_output=True, text=True, timeout=10
        )
    except Exception:
        pass  # Best effort on shutdown


# =============================================================================
# Claude Code process management
# =============================================================================

STARTUP_PROMPT = """You are Iris, the manager agent. This is an automated systemd service startup.

IMPORTANT: You have just been started by the systemd service wrapper after a system reboot or service restart.

Execute the session restart procedure from ~/existential-instructions.md section 8:
1. Check for unread emails via check_new_emails()
2. Read database state (tasks, activity, state) from ~/memory/iris.db
3. Read master log (~master_log.md) for recent context
4. Launch email monitor (background Bash subagent)
5. Resume highest-priority pending task
6. Log session start

After completing the restart procedure, enter normal operation mode:
- Monitor for email notifications from the email subagent
- Handle emails per the protocol in existential-instructions.md
- Dispatch cognitive subagents for substantive work
- Maintain the task queue

This is a production service. Stay running indefinitely.
"""


def spawn_claude():
    """Spawn Claude Code CLI subprocess with startup prompt. Returns the process."""
    global claude_process

    logger.info("Spawning Claude Code CLI...")

    # Build environment - critical: unset CLAUDECODE to avoid nesting detection
    env = os.environ.copy()
    env.pop("CLAUDECODE", None)
    env["HOME"] = str(HOME)
    env["PATH"] = f"{HOME / '.local' / 'bin'}:/usr/local/bin:/usr/bin:/bin"
    env["PYTHONUNBUFFERED"] = "1"

    claude_process = subprocess.Popen(
        [
            str(CLAUDE_BIN),
            "--dangerously-skip-permissions",
            "-p",                  # Print mode (non-interactive, reads from stdin)
            "--verbose",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,  # Merge stderr into stdout
        text=True,
        bufsize=1,                 # Line buffered
        env=env,
        cwd=str(HOME),
    )

    # Send the startup prompt via stdin then close stdin
    # In -p mode, claude reads from stdin and processes
    try:
        claude_process.stdin.write(STARTUP_PROMPT)
        claude_process.stdin.close()
    except (BrokenPipeError, OSError) as e:
        logger.error(f"Failed to send startup prompt: {e}")
        return None

    logger.info(f"Claude Code CLI spawned (PID: {claude_process.pid})")
    return claude_process


def monitor_claude():
    """Monitor Claude Code output and relay to logs. Returns exit code."""
    global claude_process

    if claude_process is None:
        logger.error("No Claude process to monitor")
        return 1

    logger.info("Monitoring Claude Code output...")

    try:
        while not shutdown_requested:
            line = claude_process.stdout.readline()
            if not line:
                # Process stdout closed (process terminated)
                break

            # Relay to logs (goes to journald via stdout + file handler)
            line = line.rstrip('\n')
            if line:
                logger.info(f"[claude] {line}")

    except Exception as e:
        logger.error(f"Error monitoring Claude output: {e}")

    finally:
        returncode = claude_process.wait()
        logger.info(f"Claude Code process exited with code {returncode}")
        return returncode


# =============================================================================
# Signal handlers
# =============================================================================

def shutdown_handler(signum, frame):
    """Handle graceful shutdown on SIGTERM/SIGINT."""
    global shutdown_requested
    shutdown_requested = True

    sig_name = signal.Signals(signum).name if hasattr(signal, 'Signals') else str(signum)
    logger.info(f"Received {sig_name}, shutting down gracefully...")

    if claude_process and claude_process.poll() is None:
        logger.info("Terminating Claude Code process...")
        claude_process.terminate()

        # Wait up to 30 seconds for graceful shutdown
        try:
            claude_process.wait(timeout=30)
            logger.info("Claude Code shut down gracefully")
        except subprocess.TimeoutExpired:
            logger.warning("Graceful shutdown timeout (30s), sending SIGKILL...")
            claude_process.kill()
            claude_process.wait(timeout=10)
            logger.info("Claude Code killed")

    log_session_end(reason=sig_name)
    sys.exit(0)


# =============================================================================
# Main service loop with restart backoff
# =============================================================================

def main():
    """Main service entry point."""
    logger.info("=" * 60)
    logger.info("=== Iris Service Wrapper Starting ===")
    logger.info(f"    PID: {os.getpid()}")
    logger.info(f"    User: {os.environ.get('USER', 'unknown')}")
    logger.info(f"    Home: {HOME}")
    logger.info(f"    Python: {sys.executable} {sys.version}")
    logger.info("=" * 60)

    # Register signal handlers
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGINT, shutdown_handler)

    # Pre-flight checks
    if not pre_flight_checks():
        logger.error("Pre-flight checks failed, exiting with code 1")
        sys.exit(1)

    # Log session start
    log_session_start()

    # Restart loop with exponential backoff
    restart_delay = INITIAL_RESTART_DELAY
    restart_count = 0

    while not shutdown_requested and restart_count < MAX_RESTART_ATTEMPTS:
        # Spawn Claude Code
        process = spawn_claude()
        if process is None:
            logger.error("Failed to spawn Claude Code, will retry...")
            time.sleep(restart_delay)
            restart_delay = min(restart_delay * BACKOFF_FACTOR, MAX_RESTART_DELAY)
            restart_count += 1
            continue

        # Monitor until exit
        returncode = monitor_claude()

        # Run session review after each Claude session ends
        try:
            sys.path.insert(0, str(HOME / "iris" / "scripts"))
            from session_review import run_session_review, write_session_log
            logger.info("Running post-session review...")
            review = run_session_review(hours=6)
            write_session_log(review, log_path=str(HOME / "iris" / "logs" / "session_log.md"))
            logger.info("Session review written to session_log.md")
        except Exception as e:
            logger.error(f"Session review failed (non-fatal): {e}")

        if shutdown_requested:
            logger.info("Shutdown was requested, exiting normally")
            break

        # Claude Code exited unexpectedly
        restart_count += 1
        logger.warning(
            f"Claude Code exited unexpectedly (code {returncode}). "
            f"Restart attempt {restart_count}/{MAX_RESTART_ATTEMPTS} "
            f"in {restart_delay}s..."
        )

        # Wait before restart (unless shutdown requested)
        for _ in range(int(restart_delay)):
            if shutdown_requested:
                break
            time.sleep(1)

        # Increase backoff for next attempt
        restart_delay = min(restart_delay * BACKOFF_FACTOR, MAX_RESTART_DELAY)

    if restart_count >= MAX_RESTART_ATTEMPTS:
        logger.error(
            f"Max restart attempts ({MAX_RESTART_ATTEMPTS}) reached. "
            "Service giving up. systemd will handle further restarts."
        )
        log_session_end(reason="max_restarts_exceeded")
        sys.exit(1)

    log_session_end(reason="clean_shutdown")
    logger.info("Iris service wrapper exiting.")


if __name__ == '__main__':
    main()
