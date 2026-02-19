#!/bin/bash
# /home/claude/iris/wiggum.sh
#
# Wiggum Loop - Controller Respawn System
# ========================================
#
# This is the core stability mechanism for Iris. It's a simple bash loop that
# ensures the controller (Iris) is always running in a tmux session.
#
# How it works:
# - Checks every 10 seconds if the "iris" tmux session exists
# - If missing (crashed, exited, or killed): spawns new controller immediately
# - If running: does nothing, checks again in 10 seconds
# - Systemd restarts wiggum itself if it dies
#
# This creates an effectively immortal controller - no matter what happens,
# it comes back within seconds.

# Load credentials from environment
# Source ~/.iris/credentials.sh before running this script
if [ -z "$POSTMARK_API_TOKEN" ]; then
    echo "WARNING: POSTMARK_API_TOKEN not set. Please source ~/.iris/credentials.sh"
fi

# Main wiggum loop - keeps the controller alive forever
while true; do
    if ! tmux has-session -t iris 2>/dev/null; then
        echo "$(date): Controller not running, spawning..."

        # Warm up the RAG embedding model before spawning the controller.
        # This pre-loads sentence-transformers (~72s cold start) so that the
        # first save_state() call inside the controller doesn't block or flood
        # logs with model-load INFO messages.  Runs in the background so wiggum
        # doesn't stall if warmup fails; the controller starts in parallel and
        # update_memory_for_file() will skip indexing until the model is warm.
        /home/claude/iris/venv/bin/python \
            /home/claude/iris/scripts/rag/warmup.py \
            >> /home/claude/iris/logs/rag-warmup.log 2>&1 &
        RAG_WARMUP_PID=$!
        echo "$(date): RAG warmup started in background (pid $RAG_WARMUP_PID)"

        # Spawn controller in tmux with iris prompt
        # Development path: /home/claude/iris/prompts/iris.md
        # Production path: /opt/ai-assistant/prompts/iris.md
        tmux new-session -d -s iris \
            "export POSTMARK_API_TOKEN=\"$POSTMARK_API_TOKEN\" && claude \"start\" --append-system-prompt-file /home/claude/iris/prompts/iris.md --dangerously-skip-permissions"

        # Give it a moment to start
        sleep 2

        echo "$(date): Controller spawned in tmux session 'iris'"
    else
        # Controller is running, check back later

        # Check watchdog heartbeat freshness (20 min threshold)
        HEARTBEAT="/tmp/iris_watchdog_heartbeat"
        FORCE_FLAG="/tmp/iris_force_restarted"
        MAX_AGE=1200  # 20 minutes

        if [ -f "$HEARTBEAT" ]; then
            FILE_TIME=$(stat -c %Y "$HEARTBEAT" 2>/dev/null || echo 0)
            NOW=$(date +%s)
            AGE=$((NOW - FILE_TIME))
            if [ "$AGE" -gt "$MAX_AGE" ]; then
                echo "$(date): Watchdog heartbeat stale (${AGE}s). Force restarting Iris..."
                date -Iseconds > "$FORCE_FLAG"
                tmux kill-session -t iris 2>/dev/null
                rm -f "$HEARTBEAT"  # Remove stale file so new session isn't immediately re-killed
                sleep 2
                echo "$(date): Session killed. Wiggum will respawn on next loop."
            fi
        fi

        sleep 2
    fi
done
