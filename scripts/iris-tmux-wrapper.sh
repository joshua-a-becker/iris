#!/bin/bash
# Iris tmux wrapper for systemd
# Starts Claude in a detached tmux session

set -e

HOME=/home/claude
CLAUDE_BIN="$HOME/.local/bin/claude"
TMUX_SESSION="iris"
LOG_FILE="$HOME/iris/logs-service/iris-service.log"

# Ensure logs directory exists
mkdir -p "$HOME/iris/logs-service"

# Log function
log() {
    echo "[$(date -Iseconds)] $1" | tee -a "$LOG_FILE"
}

# Pre-flight checks
log "=== Iris Service Starting ==="
log "Pre-flight checks..."

# Check database
if [ ! -f "$HOME/iris/memory-legacy/iris.db" ]; then
    log "ERROR: Database not found: $HOME/iris/memory-legacy/iris.db"
    exit 1
fi

# Check Claude CLI
if [ ! -x "$CLAUDE_BIN" ]; then
    log "ERROR: Claude CLI not found or not executable: $CLAUDE_BIN"
    exit 1
fi

# Check mail MCP
if [ ! -f "$HOME/iris/mail-mcp/server.py" ]; then
    log "ERROR: Mail MCP server not found"
    exit 1
fi

log "All pre-flight checks passed"

# Log to database
cd "$HOME/iris/memory-legacy"
python3 -c "
from db import log_activity
from datetime import datetime, timezone
log_activity('system', 'Service started', 'iris.service starting Claude in tmux session')
" 2>&1 | tee -a "$LOG_FILE"

# Kill any existing tmux session (cleanup)
if tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
    log "Found existing tmux session, killing it..."
    tmux kill-session -t "$TMUX_SESSION"
    sleep 2
fi

# Start tmux session with Claude and the startup prompt as a command-line argument
log "Starting tmux session '$TMUX_SESSION'..."
tmux new-session -d -s "$TMUX_SESSION" \
    "$CLAUDE_BIN" "I am Iris, the autonomous AI agent managing mail.example.com.

**Session restart detected.** Executing startup procedure per existential-instructions.md section 8:

1. Check for new emails
2. Handle any unread emails (confirm receipt per protocol)
3. Restart email monitoring loop (5-second polling, background Bash agent)
4. Check database state for pending tasks
5. Resume highest-priority pending task

Starting now." --dangerously-skip-permissions \
    2>&1 | tee -a "$LOG_FILE"

log "Tmux session started successfully. Attach with: tmux attach -t $TMUX_SESSION"

# Now just wait - tmux session runs independently
# This script stays alive so systemd can monitor it
log "Monitoring tmux session..."

while true; do
    if ! tmux has-session -t "$TMUX_SESSION" 2>/dev/null; then
        log "ERROR: Tmux session died unexpectedly"
        exit 1
    fi
    sleep 10
done
