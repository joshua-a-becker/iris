# AI Assistant Architecture (Iris + Wiggum)

## Overview

This document describes the architecture for a self-managing AI assistant that lives on a dedicated Linux server (Digital Ocean, 2-core/4GB RAM) and communicates with its operator primarily over email. The assistant behaves as an independent entity — more like a colleague with their own office than a tool you invoke. You email it tasks, it works through them autonomously, and emails back results. You can also "drop by its office" at any time by attaching to its tmux session and watching it work or intervening directly.

The system is built around a simple insight: **Claude Code agents work best in bounded sessions with clear context**. Rather than running one long-lived agent that eventually accumulates confusion, the system uses **voluntary context clearing** — the assistant runs for multiple tasks, but when it senses context getting heavy, it checkpoints its state to disk and exits. A persistent bash loop (the "wiggum loop") immediately respawns it fresh. This mimics how humans work — do focused work, take a break, review your notes, resume. The external state file is the assistant's "memory."

The core communication flow is: **Email arrives → controller notices and handles it → queues or acts immediately → spawns worker subagents for complex tasks → checkpoints progress → voluntarily exits when context gets heavy → wiggum loop spawns fresh controller → controller loads state and continues.**

The controller runs inside a tmux session so the operator can attach at any time for direct observation or interaction.

---

## System Diagram

```
┌─────────────────────────────────────────────────────┐
│  SYSTEMD: ai-wiggum.service                         │
│  Persistent bash loop                               │
│  Job: Keep controller alive, respawn if it exits    │
└────────────────┬────────────────────────────────────┘
                 │
                 ▼
      tmux:iris ← CONTROLLER (Iris)
                 │ Monitors for new email (poll or watchdog)
                 │ Receives email → send ack → queue or handle
                 │ Evaluates task queue
                 │ Spawns worker subagents for complex tasks
                 │ Waits for workers → processes results
                 │ Updates state.json continuously
                 │
                 │ Self-assessment loop:
                 │   ├─ Context healthy? → Continue working
                 │   └─ Context heavy? → Save state, exit gracefully
                 │
                 │ On exit (graceful or crash):
                 │   → wiggum detects, respawns controller immediately
                 │   → new controller loads state.json, resumes
                 │
                 ├── WORKER SUBAGENTS (ephemeral)
                 │   Background claude-code subagents
                 │   Do focused work (research, drafting, posting, etc.)
                 │   Report results back to controller
                 │   Terminate when task completes
                 │
                 └── EMAIL WATCHDOG (optional helper)
                     Python script monitoring mailbox
                     Writes flag file when new email detected
                     Controller checks flag or watchdog can signal

    ┌────────────────────────────────────────────┐
    │  PERSISTENT STORAGE                        │
    │                                            │
    │  Flat files:                               │
    │    /var/lib/ai-assistant/state.json        │
    │      - Current context and active tasks    │
    │      - Personality notes and learnings     │
    │      - Self-awareness ("I'm Iris")         │
    │      - Recent activity summary             │
    │                                            │
    │    /var/lib/ai-assistant/tasks/{id}/       │
    │      - checkpoint.json                     │
    │      - result/                             │
    │      - attachments/                        │
    │                                            │
    │  Database (~/memory/iris.db):              │
    │    - emails (full archive)                 │
    │    - tasks (history and active)            │
    │    - activity log                          │
    │    - key-value state                       │
    └────────────────────────────────────────────┘
```

---

## Layer 0: System Services

These are plain bash/systemd — no AI, no API calls. Their only job is to be unkillable and to spawn the controller at the right time.

### Wiggum Loop (ai-wiggum.service)

The core stability mechanism. Runs as a systemd service. Keeps the controller alive.

```bash
#!/bin/bash
# /opt/ai-assistant/wiggum.sh

while true; do
    if ! tmux has-session -t iris 2>/dev/null; then
        echo "$(date): Controller not running, spawning..."

        # Spawn controller in tmux
        tmux new-session -d -s iris \
            "claude-code --prompt-file /opt/ai-assistant/prompts/iris.md"

        # Give it a moment to start
        sleep 2
    else
        # Controller is running, check back later
        sleep 10
    fi
done
```

```ini
# /etc/systemd/system/ai-wiggum.service
[Unit]
Description=AI Assistant Wiggum Loop (Controller Respawn)
After=network.target

[Service]
Type=simple
User=claude
WorkingDirectory=/home/claude
ExecStart=/opt/ai-assistant/wiggum.sh
Restart=always
RestartSec=5
MemoryMax=256M

[Install]
WantedBy=multi-user.target
```

**How it works:**
- Checks every 10 seconds if controller tmux session exists
- If missing (crashed, exited, or killed): spawns new controller immediately
- If running: does nothing, checks again in 10 seconds
- Systemd restarts wiggum itself if it dies

**Result:** Controller is effectively immortal. No matter what happens, it comes back.

### Health Monitor (ai-health.service) - Optional

Separate systemd service that watches for resource issues and sends alerts.

Key responsibilities:
- Kill any claude-code process exceeding 3GB RAM (safety limit)
- Alert operator if wiggum loop itself dies
- Monitor disk usage (agents can generate a lot of output)
- Log system-level events for debugging

---

## Layer 1: The Controller (Iris)

The controller is **Iris** — the AI assistant. It's a Claude Code instance that runs in tmux session `iris`. It handles everything: email monitoring, task management, work execution, state maintenance.

### Controller Responsibilities

1. **Email monitoring** - Poll for new email or use watchdog helper
2. **Email handling** - Read, triage, send acks, queue tasks or act immediately
3. **Task queue management** - Prioritize and dispatch work
4. **Worker orchestration** - Spawn subagents for complex tasks, collect results
5. **State maintenance** - Continuously update state.json
6. **Context self-assessment** - Decide when to voluntarily exit for refresh
7. **Personality continuity** - Maintain "self" across restart cycles

### Controller Lifecycle

```
1. START (fresh spawn from wiggum)
   ├─ Load state.json (external memory from previous session)
   ├─ Read database state (tasks, recent activity)
   ├─ Restore personality and context
   └─ Log session start

2. MAIN LOOP (runs until voluntary exit)
   ├─ Check for new email (poll or watchdog flag)
   │  └─ If email: read, ack immediately, queue or handle
   │
   ├─ Evaluate task queue
   │  ├─ High priority work? Dispatch worker subagent (background)
   │  ├─ Simple task? Handle directly
   │  └─ Nothing? Wait for email
   │
   ├─ Wait for worker completion (if dispatched)
   │  └─ Process results, update state, email if needed
   │
   ├─ Self-assess context health
   │  ├─ Token count high? Context feels confused?
   │  ├─ If healthy: continue main loop
   │  └─ If heavy: goto VOLUNTARY EXIT
   │
   └─ Loop back to check email

3. VOLUNTARY EXIT (clean checkpoint)
   ├─ Save complete state.json
   │  ├─ Active tasks and progress
   │  ├─ Personality notes ("I'm Iris, was working on X")
   │  ├─ Recent context ("Last email was about Y")
   │  └─ Self-notes for next session
   │
   ├─ Update database (task status, activity log)
   ├─ Log exit reason ("Voluntary context refresh")
   └─ Exit gracefully
      → tmux session dies
      → wiggum detects, spawns fresh controller (goto START)

4. CRASH (unexpected termination)
   → tmux session dies
   → wiggum detects, spawns fresh controller (goto START)
   → new controller loads state.json, resumes from last checkpoint
```

### Email Monitoring

**Option A: Direct polling (simple)**
```python
# Inside controller's main loop
import time
from mail_tools import check_new_emails

while True:
    emails = check_new_emails()
    if emails:
        handle_emails(emails)

    # Do other work...

    # Check context health
    if self.context_heavy():
        self.voluntary_exit()

    time.sleep(5)  # Poll every 5 seconds
```

**Option B: Watchdog helper (cleaner)**
```python
# /opt/ai-assistant/email-watchdog.py
# Runs as background subprocess of controller

import time, os

FLAG_FILE = "/tmp/iris-new-email"

while True:
    result = check_new_emails()
    if "unread" in result:
        # Signal controller
        open(FLAG_FILE, 'w').write(result)
        break  # Exit, controller will restart me
    time.sleep(5)
```

Controller spawns watchdog at startup, checks flag file in main loop, restarts watchdog when it exits.

### Worker Subagents

For complex tasks (drafting long emails, research, Moltbook posts, multi-file edits), the controller spawns **worker subagents** using Claude Code's Task tool.

**Always run in background:**
```python
Task(
    subagent_type="general-purpose",
    description="Draft Moltbook post",
    run_in_background=True,
    prompt="""
    Read ~/docs/services/moltbook.md for account details.
    Draft a Moltbook post about collective intelligence.
    Use JSON file method: write to /tmp/post.json, run ~/moltbook-post.py
    Report back: success/failure, post ID, any errors.
    """
)
```

**Controller waits for completion:**
```python
# Poll TaskOutput until worker completes
while True:
    output = TaskOutput(task_id=worker_id, block=False, timeout=1000)
    if output.status == "completed":
        process_worker_results(output)
        break

    # While waiting, can still check for urgent email
    check_email_flag()
    time.sleep(10)
```

**Worker characteristics:**
- Ephemeral (terminates after task)
- Focused (single logical unit of work)
- Background (controller remains responsive)
- Typical duration: 2-10 minutes
- Reports results back to controller

### Context Self-Assessment

The controller periodically checks if it needs a voluntary refresh:

**Triggers for voluntary exit:**
- Token count exceeds threshold (e.g., 80% of context window)
- Task completion count (e.g., after 5-10 tasks)
- Time-based (e.g., every 2 hours)
- Self-detected confusion ("I'm losing track of state")
- Operator command (via email or tmux interaction)

**Before exiting:**
```python
def voluntary_exit(self):
    print("Context getting heavy - saving state for refresh...")

    state = {
        "last_session_end": now(),
        "exit_reason": "voluntary_context_refresh",
        "personality": {
            "name": "Iris",
            "awareness": "I'm the same assistant, just refreshed",
            "recent_tone": "Professional, occasional dragon humor",
        },
        "active_tasks": [...],
        "recent_context": "Was working on X, Joshua asked about Y",
        "next_steps": ["Check email", "Resume task Z if not complete"],
        "self_notes": "Joshua prefers CSV outputs. Moltbook rate limit: 1 post/2hrs"
    }

    save_state_json(state)
    log_activity("session", "Voluntary exit for context refresh")

    print("State saved. Exiting gracefully. Wiggum will respawn me fresh.")
    exit(0)
```

---

## Layer 2: State and Memory

### State File (state.json)

The controller's external memory. Critical for continuity across restart cycles.

```json
{
  "last_session_end": "2026-02-16T14:30:00Z",
  "exit_reason": "voluntary_context_refresh",

  "personality": {
    "name": "Iris",
    "identity": "AI assistant for Joshua",
    "awareness": "I'm the same assistant across sessions, just with refreshed context",
    "recent_tone": "Professional with occasional dragon-themed humor",
    "relationship_notes": "Joshua prefers frequent updates, CSV over JSON for data"
  },

  "active_tasks": [
    {
      "task_id": "abc123",
      "description": "Pull latest Prolific data",
      "status": "in_progress",
      "progress": "Downloaded 3/5 sources, parsed to CSV",
      "next_steps": ["Parse remaining 2 sources", "Merge datasets", "Email results"],
      "worker_id": null,
      "started_at": "2026-02-16T14:00:00Z"
    }
  ],

  "recent_context": {
    "last_email": {
      "from": "owner-work@example.com",
      "subject": "Prolific data pull",
      "summary": "Asked for latest dataset with demographics",
      "timestamp": "2026-02-16T13:55:00Z"
    },
    "last_action": "Dispatched worker for data processing",
    "waiting_for": "Worker abc123 to complete data merge"
  },

  "task_queue": {
    "total_pending": 2,
    "highest_priority": "Fix CSS on experiment page (priority 2)",
    "queue_snapshot": [...]
  },

  "self_notes": [
    "Joshua prefers CSV format for datasets",
    "Always email results when task completes, don't just save to disk",
    "Moltbook rate limit: 1 post per 2 hours, check before posting",
    "When Prolific tasks arrive, verify API credentials first"
  ],

  "statistics": {
    "total_sessions": 147,
    "tasks_completed_today": 3,
    "context_refreshes_today": 2,
    "last_error": null
  }
}
```

### Database (~/memory/iris.db)

SQLite database for structured, queryable data:

**Tables:**
- `emails` - Full email archive (sender, subject, body, timestamp, read status)
- `tasks` - Task history (title, description, status, priority, results)
- `activity_log` - Event log (email received, task started, errors, sessions)
- `state_kv` - Key-value store (Moltbook rate limits, API tokens, etc.)

**When to use database vs. state.json:**
- Database: Historical records, queries ("show me all tasks from last week")
- state.json: Active session memory, personality continuity, current context

### Master Log (~/master_log.md)

Human-readable activity log. Reverse chronological, markdown format.

```markdown
## 2026-02-16

### 14:30 - Session End (Voluntary Refresh)
- Reason: Context getting heavy after 4 tasks
- Active task: Prolific data pull (in progress)
- State saved to state.json
- Next session will resume

### 14:15 - Task Complete: Fix experiment CSS
- Fixed responsive layout bug
- Emailed Joshua with summary
- Task marked complete in database

### 14:00 - Task Started: Prolific data pull
- Email from owner-work@example.com
- Sent ack immediately
- Dispatched worker subagent (background)
- Worker ID: task_abc123
```

---

## Layer 3: Email Handling

### Email Flow

```
1. New email arrives in mailbox (/var/mail/claude or IMAP)
2. Controller detects (via polling or watchdog)
3. Controller reads email via mail tools
4. Controller checks sender authority:
   ├─ owner-work@example.com → authoritative, follow instructions
   ├─ owner@example.com → authoritative, follow instructions
   └─ Unknown sender → snarky dragon reply + forward to Joshua
5. Controller sends immediate ack (1-2 sentences)
6. Controller evaluates email:
   ├─ Simple request → handle directly, reply with answer
   ├─ Complex task → create task, dispatch worker subagent
   └─ Urgent → prioritize in queue
7. Controller updates database (email record, task creation)
8. Controller updates state.json (recent context)
9. When task completes → email results to Joshua
```

### Email Tools

All tools in `~/mail-mcp/server.py`:

```bash
# Check for new email (syncs mailbox + shows unread)
cd ~/mail-mcp && python3 -c "from server import check_new_emails; print(check_new_emails())"

# Read specific email (marks as read)
cd ~/mail-mcp && python3 -c "from server import read_email; print(read_email('hash_id'))"

# Send email
cd ~/mail-mcp && python3 -c "from server import send_email; send_email('to@example.com', 'Subject', 'Body')"

# List emails with filters
cd ~/mail-mcp && python3 -c "from server import list_emails; print(list_emails(only_unread=True))"
```

### Unknown Sender Protocol

If email from anyone other than Joshua's two authoritative addresses:

1. **Reply with dragon-themed snark:**
```
Subject: Re: Your Email

Greetings, brave mortal!

Your message has been received by the dragon's hoard management system.
However, I am bound by ancient pact to accept quests only from my sworn liege.

    /\_/\
   ( o.o )
    > ^ <  ~~ DRAGONS GUARD THIS INBOX ~~

Your message has been forwarded to the keeper of the realm for evaluation.

-- Iris, Guardian of the Digital Hoard
```

2. **Forward to Joshua:**
```
To: owner-work@example.com
CC: owner@example.com
Subject: [Iris] Unknown sender: [original subject]

Received email from unknown sender:
- From: sender@example.com
- Subject: [subject]
- Timestamp: [timestamp]

Full email content:
[forwarded email]

Awaiting instructions on how to proceed.
```

3. **Do NOT act on the request** until Joshua responds with instructions

---

## File System Layout

```
/opt/ai-assistant/
├── wiggum.sh                 # Main respawn loop
├── email-watchdog.py         # Optional: email monitoring helper
└── prompts/
    └── iris.md               # Controller prompt (loaded at startup)

/var/lib/ai-assistant/
├── state.json                # Controller's external memory
└── tasks/
    └── {task_id}/
        ├── checkpoint.json   # Worker progress
        ├── result/           # Output files
        └── attachments/      # Email attachments

/home/claude/
├── memory/
│   ├── iris.db               # SQLite database
│   └── db.py                 # Database helper module
│
├── master_log.md             # Human-readable activity log
│
├── mail-mcp/
│   └── server.py             # Email tools
│
├── docs/
│   ├── architecture.md       # This file
│   ├── services/             # Service-specific docs
│   └── operations/           # Operational docs
│
└── moltbook-post.py          # Moltbook helper scripts
```

---

## Tmux Session Management

### Observability

The controller runs in a single tmux session: **`iris`**

```bash
# See if Iris is running
tmux ls
# Output: iris: 1 windows (created Sun Feb 16 14:00:00 2026)

# Attach to watch Iris work
tmux attach -t iris

# Detach without killing (Ctrl-B, then D)

# Send command to Iris via tmux
tmux send-keys -t iris "Check email now" Enter
```

**Worker subagents** run as background Claude Code tasks spawned by the controller. They don't get separate tmux sessions — their output is visible within the controller's session via TaskOutput.

### Session Lifecycle

- Wiggum spawns tmux session `iris` with controller
- Controller runs until voluntary exit or crash
- On exit, tmux session dies (default behavior)
- Wiggum detects missing session, spawns new one immediately
- New controller loads state.json, resumes where previous left off

**Session persistence:** The **tmux session** is ephemeral (dies on exit). The **assistant's continuity** comes from state.json, not from keeping the session alive.

---

## Resource Management

On a 2-core/4GB RAM server with 8GB swap:

**Resource allocation:**
- Wiggum loop: ~5MB (sleeping bash process)
- Controller: 200-500MB (Claude Code instance)
- Worker subagent: 200-500MB (when active)
- Total peak usage: ~1GB with controller + 1 worker

**Operating mode:**
- Default: Controller + 0-1 worker subagent
- Maximum: Controller + 2 workers (if urgent parallel work needed)
- Swap provides headroom for brief parallel operation

**Limits enforced by health monitor:**
- Kill any claude-code process exceeding 3GB RAM
- Alert operator if system memory pressure
- Disk usage monitoring (logs, task outputs)

**Controller voluntary exit triggers:**
- Context token count > 80% of window
- After N tasks completed (configurable, default: 10)
- After N hours runtime (configurable, default: 4)
- Self-detected confusion
- Operator request

---

## Startup and Recovery

### System Boot

1. Systemd starts `ai-wiggum.service`
2. Wiggum loop starts, detects no controller running
3. Wiggum spawns controller in tmux session `iris`
4. Controller starts fresh (no state.json yet, or loads existing)
5. Controller begins email monitoring and task processing

### Controller Startup Procedure

When controller starts (fresh or respawn):

```
1. Check for state.json
   ├─ Exists → Load previous session state
   └─ Missing → Initialize blank state

2. Load database state
   ├─ Tasks: in_progress, pending
   ├─ Recent activity: last 10 events
   └─ Key-value state: rate limits, etc.

3. Restore personality from state.json
   └─ "I'm Iris, same assistant, refreshed context"

4. Check for unread email immediately
   └─ Handle any waiting messages

5. Resume active tasks
   ├─ Tasks marked in_progress → evaluate if need to resume or restart
   └─ Pending high-priority tasks → dispatch workers

6. Start email monitoring (poll loop or spawn watchdog)

7. Log session start to database and master_log.md

8. Enter main loop
```

### Crash Recovery

Controller crashes or gets killed:

```
1. Tmux session dies
2. Wiggum detects missing session (within 10 seconds)
3. Wiggum spawns new controller
4. New controller loads state.json (last checkpoint before crash)
5. New controller resumes from last known state
   ├─ If worker was running: check if still running, or restart task
   ├─ If waiting for email: resume waiting
   └─ If in middle of action: review state, decide how to proceed
6. Continue normally
```

**Data loss:** Minimal. State.json is updated continuously (after each significant action). Worst case: lose a few minutes of state since last write.

---

## Self-Refinement and Learning

### Self-Notes in state.json

The controller maintains `self_notes` that persist across sessions:

```json
{
  "self_notes": [
    "Joshua prefers CSV format for data outputs",
    "Always email results when done, don't just save to disk",
    "Moltbook rate limit: 1 post/2 hours",
    "When debugging, Joshua prefers detailed logs over summaries",
    "Dragon-themed humor is welcome in responses to unknown senders"
  ]
}
```

**How notes accumulate:**
- Joshua gives feedback via email → controller adds note
- Operator gives feedback via tmux → controller adds note
- Controller observes pattern → proposes note addition
- Notes are reviewed periodically, pruned if outdated

### Prompt Evolution

The controller's prompt (`/opt/ai-assistant/prompts/iris.md`) can evolve:

1. Controller proposes prompt edit based on learnings
2. Controller emails Joshua with proposed change
3. Joshua approves or modifies
4. Operator edits prompt file
5. Next controller restart loads updated prompt

**Goal:** System gets better at its job through practice, feedback, and reflection — like training a colleague.

---

## Key Design Principles

### 1. Voluntary Context Clearing > Forced Compacting

The controller decides when to refresh, not when forced by token limits. This preserves agency and allows graceful checkpointing.

### 2. External State = Memory

state.json is not a "crash recovery backup" — it's the primary memory system. The controller is ephemeral, state.json is permanent.

### 3. Personality Persists, Context Resets

Across restart cycles, the controller maintains:
- ✅ Identity ("I'm Iris")
- ✅ Learnings (self-notes)
- ✅ Relationships (Joshua's preferences)
- ✅ Active work (task progress)

But resets:
- ✅ Token count (fresh context window)
- ✅ Accumulated confusion
- ✅ Conversation threads (except what's summarized in state)

### 4. Simple Components, Robust System

- Wiggum loop: dumb bash, can't fail
- Controller: smart but ephemeral, crashes don't matter
- Workers: focused and disposable
- State files: simple JSON, human-readable
- Result: system is greater than sum of parts

### 5. Observable and Interactable

- Tmux sessions: operator can watch and intervene
- State files: operator can read and edit
- Logs: human-readable activity history
- Email: two-way communication channel

The operator is never locked out. The system is transparent.

---

## Comparison to Original Iris

| Aspect | Original Iris | Iris + Wiggum |
|--------|---------------|---------------|
| **Persistence** | Runs until crash/confusion | Runs until voluntary exit |
| **Recovery** | Manual restart | Automatic respawn (wiggum) |
| **Context** | Accumulates until forced compact | Voluntary refresh before confusion |
| **Memory** | In-context + ad-hoc files | state.json + database |
| **Observability** | Limited | tmux session |
| **Stability** | Empirically unstable | Designed for long-term stability |
| **Personality** | Continuous presence | Continuous presence (same) |
| **Complexity** | Lower | Slightly higher (wiggum loop) |
| **Architecture** | Single agent | Single agent + respawn wrapper |

**Key insight:** Same assistant, same personality, same capabilities — just wrapped in a stability framework that enables voluntary context management and automatic recovery.

---

## Implementation Checklist

- [ ] Set up wiggum loop script and systemd service
- [ ] Define state.json schema
- [ ] Write controller prompt (iris.md) with:
  - [ ] Personality definition
  - [ ] Email handling protocol
  - [ ] Context self-assessment logic
  - [ ] Voluntary exit procedure
  - [ ] State loading/saving procedures
- [ ] Set up tmux session management
- [ ] Configure email monitoring (poll or watchdog)
- [ ] Test crash recovery (kill controller, verify respawn)
- [ ] Test voluntary exit (trigger context refresh)
- [ ] Test state persistence (verify continuity across restart)
- [ ] Set up health monitor (optional but recommended)
- [ ] Configure resource limits
- [ ] Document operator procedures (attach to tmux, check logs, etc.)

---

## Maintenance and Operations

### Monitoring

**Check if Iris is running:**
```bash
tmux ls | grep iris
# or
systemctl status ai-wiggum
```

**View recent activity:**
```bash
tail -n 50 ~/master_log.md

# or from database
cd ~/memory && python3 -c "from db import get_recent_activity; print(get_recent_activity(20))"
```

**Check current state:**
```bash
cat /var/lib/ai-assistant/state.json | jq .
```

### Intervention

**Attach to watch Iris work:**
```bash
tmux attach -t iris
```

**Send command to Iris:**
```bash
# Via tmux
tmux send-keys -t iris "Check email now and report status" Enter

# Via email
echo "Report your current status" | mail -s "Status check" claude@mail.example.com
```

**Force context refresh:**
```bash
# Via tmux
tmux send-keys -t iris "Save state and exit for refresh now" Enter

# or kill session (wiggum will respawn)
tmux kill-session -t iris
```

**View logs:**
```bash
# System logs
journalctl -u ai-wiggum -f

# Master log
tail -f ~/master_log.md
```

### Debugging

**Controller not respawning:**
```bash
# Check wiggum service
systemctl status ai-wiggum
journalctl -u ai-wiggum -n 50

# Check for errors in wiggum script
bash -x /opt/ai-assistant/wiggum.sh
```

**Controller repeatedly crashing:**
```bash
# Attach to see crash
tmux attach -t iris

# Check state.json for corruption
cat /var/lib/ai-assistant/state.json | jq .

# Check system resources
htop
df -h
```

**Email not being processed:**
```bash
# Check mailbox
mail

# Test email tools
cd ~/mail-mcp && python3 -c "from server import check_new_emails; print(check_new_emails())"

# Check mail logs
tail -f /var/log/mail.log
```

---

## Future Enhancements

### Considered but not yet implemented:

1. **Multi-modal input** - Attachments, images, voice notes
2. **Proactive suggestions** - "I noticed X, should I do Y?"
3. **Scheduled tasks** - "Every Monday at 9am, do X"
4. **Multiple concurrent workers** - Parallel task execution (currently 1-2 max)
5. **Web interface** - Dashboard for status, logs, task queue
6. **Mobile notifications** - Push alerts for task completion
7. **Collaborative mode** - Multiple operators, shared task queue
8. **Learning from history** - Analyze past tasks to improve future performance

### Scaling considerations:

Current architecture supports:
- ~10-50 emails per day
- ~5-20 tasks per day
- Single operator (Joshua)
- 2-core/4GB server

If volume increases significantly:
- Upgrade server (more cores, more RAM)
- Consider multiple worker pools
- Add queue prioritization algorithms
- Implement task batching for efficiency

---

## Conclusion

This architecture balances **simplicity** (single controller agent, minimal components) with **robustness** (automatic respawn, voluntary context clearing, persistent state). It preserves the personality and continuity of the original Iris while adding the stability mechanisms needed for long-term reliability.

The key innovation is **voluntary context management** — the controller decides when to take a break and refresh, rather than running until forced to stop by token limits or confusion. Combined with automatic respawn via the wiggum loop, this creates a system that is both resilient and maintainable.

The assistant is **observable** (tmux), **recoverable** (state.json), and **improvable** (self-notes, prompt evolution). It's designed to get better over time, like any good colleague.
