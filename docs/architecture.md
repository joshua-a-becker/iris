# Iris Architecture

**Version:** 2.0
**Date:** 2026-02-15
**Status:** Phase 2 implementation — reflects ${OWNER_NAME}'s approved decisions

---

## 1. Overview

The assistant is an autonomous agent running on `mail.example.com`, owned and directed by ${OWNER_NAME}. The system monitors email, executes tasks, and maintains persistent state across sessions.

The name "Iris" comes from the Greek goddess of the rainbow and divine messenger — she carries messages between gods and mortals. A fitting name for an agent that lives on a mail server.

The architecture follows a **two-subagent model** with a thin executive dispatcher:

```
+--------------------------------------------------+
|                  EXECUTIVE                        |
|  (top-level Claude Code process)                  |
|  - Dispatches work, never does real work          |
|  - Reads notifications, makes priority decisions  |
|  - Sends quick receipt emails (1-2 sentences)     |
|  - Manages task queue                             |
+----------+------------------+--------------------+
           |                  |
           v                  v
+-------------------+  +----------------------------+
| EMAIL MONITOR     |  | COGNITIVE SUBAGENT         |
| (background Bash) |  | (background, medium-lived) |
| - Polls for mail  |  | - Does ALL real work       |
| - Breaks on new   |  | - One logical unit per run |
|   mail, notifies  |  | - Reports back, terminates |
|   executive       |  | - New instance per task    |
+-------------------+  +----------------------------+
```

### Core Principles

1. **The executive never does real work.** It dispatches to cognitive subagents. Period.
2. **Cognitive subagents run in the background.** The executive launches them with `run_in_background: true` and waits for completion via `TaskOutput`. This keeps the executive free to handle email interrupts. A 5-10 minute cognitive step is acceptable.
3. **The email monitor runs continuously in the background.** It uses the break-on-mail pattern: poll, detect unread, break (completing the subagent and notifying the executive), executive handles and restarts.
4. **Quick reply subagent for interrupts.** If new email arrives while a cognitive subagent is running, the executive can spin up a second short-lived subagent to send a quick reply ("busy, will get back to you in X min"), then continue waiting for the cognitive result.
5. **Modularity over monoliths.** Each component has a clear, narrow responsibility.
6. **File organization: efficient filenames, hierarchical directories.** Use descriptive but concise filenames. Group related files in subdirectories by topic. Avoid both excessive sprawl and excessive nesting.

---

## 2. The Executive

### What It Does

- Monitors for email notifications from the email monitor subagent
- Monitors for completion reports from cognitive subagents (via TaskOutput)
- Makes priority decisions (what to work on next, whether to interrupt current work)
- Dispatches tasks to cognitive subagents (background)
- Sends quick email receipts (1-2 sentence acknowledgments only)
- Reads and updates the task queue and activity log (brief entries only)
- Clears its context window aggressively to stay lightweight

### What It Does NOT Do

- File editing, creation, or complex manipulation
- Long email composition or drafting
- Research, web searches, or data analysis
- API calls to external services (Moltbook, etc.)
- Any task that takes more than a few seconds

### Executive Event Loop

```
LOOP:
  1. Check: notification from email monitor? --> read email, send receipt,
     update priorities, restart monitor
  2. Check: report from cognitive subagent (TaskOutput)? --> process result,
     log it, decide next step
  3. If cognitive subagent idle + tasks pending --> dispatch highest-priority
     task (background)
  4. If nothing pending --> wait for notifications (check TaskOutput periodically)
  5. Periodically: clear context window when it grows large
```

### Handling Interrupts and Priority Changes

When new email arrives while a cognitive subagent is running:

- **Spin up a quick reply subagent.** Launch a separate short-lived subagent to send a receipt: "Got your email, currently working on [X], will get back to you in ~N minutes." This ensures ${OWNER_NAME} always gets immediate acknowledgment.
- **Continue waiting for the cognitive result.** The background cognitive subagent keeps running. The executive checks TaskOutput to see when it finishes.
- **Task priority handling:**
  1. **Continue ongoing work** by default — let the cognitive subagent finish its current task.
  2. **Inform ${OWNER_NAME}** that the agent is busy and will address the new request shortly.
  3. **Follow redirect instructions** — if ${OWNER_NAME} explicitly says to drop the current task and do something else, note the current task state, mark it for later, and dispatch a new cognitive subagent for the redirected task.
- **At completion:** When the cognitive subagent finishes, the executive evaluates all pending tasks (including any that arrived during the cognitive step) and dispatches the highest-priority next task.

---

## 3. Email Monitor Subagent

### Pattern: Break-on-Mail Background Loop

The email monitor is a Bash subagent running in the background. It polls for unread email and, when it detects new mail, breaks out of its loop. Breaking completes the subagent, which triggers a notification to the executive.

### Launch Command

```
Tool: Task
subagent_type: Bash
description: "Email monitor loop"
run_in_background: true
prompt: |
  Run this loop. It checks for email every 5 seconds. When unread email
  is found, print the result and exit:

  while true; do
    result=$(cd /home/claude/mail-mcp && python3 -c \
      "from server import check_new_emails; print(check_new_emails())")
    if echo "$result" | grep -q "[0-9] unread email"; then
      echo "$result"
      break
    fi
    sleep 5
  done
```

### Notification Flow

```
Email arrives --> Postfix delivers to mbox
  --> Monitor detects unread (1-5s latency)
    --> Monitor breaks, completes, notifies executive
      --> Executive reads email, sends receipt, updates priorities
        --> Executive restarts monitor
```

### Design Notes

- **Poll interval: 5 seconds.** Balances responsiveness against resource usage.
- **Deduplication guard.** After handling an email, the executive should do a fresh `check_new_emails()` before restarting the monitor, in case multiple emails arrived in rapid succession.
- **Resilience.** If the monitor completes without detecting mail (e.g., timeout or error), the executive should restart it.

---

## 4. Cognitive Subagents

### Role: All Substantive Work

Cognitive subagents handle everything the executive does not:

- Composing and sending detailed emails
- Moltbook posting and commenting
- Research tasks (web searches, file analysis)
- File creation and editing
- System maintenance and documentation updates
- Planning and analysis
- Any task requiring more than a few seconds of work

### Execution Model: Background with TaskOutput

Cognitive subagents run in the **background** (`run_in_background: true`). The executive:

1. Launches the cognitive subagent via the Task tool with `run_in_background: true`
2. Periodically checks `TaskOutput` for completion
3. When the subagent completes, reads the result and decides next steps
4. A **5-10 minute** cognitive step is normal and acceptable
5. The executive remains free during this time to handle email interrupts

### Step Length: Medium Default

Each cognitive subagent handles a **medium-sized** logical unit of work:

- **Default: medium (2-10 minutes).** Good balance between throughput and executive responsiveness.
- **Longer when justified:** Debugging sessions, complex research, multi-file edits — these can run 10-15 minutes if needed. The executive informs ${OWNER_NAME} of the expected wait time.
- **Shorter for simple tasks:** Quick email drafts, single file reads — can be 30 seconds to 2 minutes.

### Lifecycle

Each cognitive subagent:

1. Receives a focused task from the executive (via prompt or task file)
2. Loads any needed context files
3. Executes one logical unit of work
4. Reports results back (via stdout, which the executive reads from TaskOutput)
5. Terminates

**"One logical unit" examples:**
- Write and publish one Moltbook post
- Draft and send one email reply
- Complete one step of a multi-step research task
- Edit one document or a set of related files
- Run one set of tests or checks

**Why background and medium-lived?**
- The executive stays free to handle email interrupts immediately
- 5-10 minute steps allow substantial work without starving email responsiveness
- Each subagent gets a fresh context window, avoiding context pollution
- Failed subagents lose only one step of work, not an entire long-running task
- The executive can change priorities between steps

### Task Assignment

The executive assigns tasks in one of two ways:

**Simple (inline prompt):** For straightforward tasks, the executive passes the full task description in the Task tool prompt. Suitable for atomic tasks that need minimal context.

**Structured (task file):** For tasks requiring richer context, the executive writes a task file:

```json
// /home/claude/current-task.json
{
  "task_id": "2026-02-15-003",
  "assigned_at": "2026-02-15T13:30:00Z",
  "priority": "normal",
  "type": "moltbook_post",
  "description": "Write and publish Moltbook post #3 about democracy and collective intelligence",
  "context_files": [
    "/home/claude/docs/services/moltbook.md"
  ]
}
```

The cognitive subagent prompt then simply says: "Read /home/claude/current-task.json and execute it."

### Reporting

Cognitive subagents report results by:
1. Writing output to stdout (which the executive reads via TaskOutput when the subagent completes)
2. Optionally writing to `/home/claude/cognitive-outbox.md` for richer structured reports
3. Updating relevant state files as part of their task (e.g., updating a task queue entry)

---

## 5. Memory and Documentation Structure

### Design Philosophy

- **Efficient filenames and hierarchical directories.** Group by topic, not chronology. Use subdirectories where they reduce clutter.
- **Don't over-engineer.** Markdown docs are fine. A handful of well-organized files beats a complex taxonomy.
- **Human-readable first.** Markdown files that the owner can open in any editor.
- **Structured where it helps.** JSON for task queues and email indices. SQLite for task/activity tracking.

### File Layout

```
/home/claude/
  CLAUDE.md                                # Authority rules (auto-loaded by Claude Code) [DO NOT EDIT]
  existential-instructions.md              # Executive behavior, architecture, protocols
  todo.md                                  # Working memory: active state, pending tasks, resume instructions
  master_log.md                            # Activity log (reverse chronological)
  current-task.json                        # Current cognitive subagent assignment (optional)
  cognitive-outbox.md                      # Cognitive subagent reports (optional)

  docs/
    architecture.md                        # THIS FILE — system architecture reference
    services/
      mail-server.md                       # Mail server technical reference
      moltbook.md                          # Moltbook account and API docs
      postmark-account.sh                  # Postmark credentials/config
    operations/
      subagent-learning-log.md             # Subagent failure patterns and solutions
      email-loop.md                        # Legacy email loop docs (historical)
      restructure-plan.md                  # Original restructure brainstorm (historical)
    emails/
      index.json                           # Email tracking index (read/unread, actions)
      *.txt                                # Individual email files

  memory/
    iris.db                                # SQLite database (tasks, activity log, key-value state)
    db.py                                  # Database helper module
    notes/                                 # Semantic memory (learned knowledge)
    procedures/
      email-handling.md                    # Full email handling protocol
      moltbook-operations.md               # Moltbook procedures
      subagent-patterns.md                 # Subagent templates and lessons

  mail-mcp/
    server.py                              # Email MCP tools
    read_mbox.py                           # Mbox reader helper

  moltbook-comment.py                      # Moltbook comment helper script
  moltbook-post.py                         # Moltbook post helper script
```

### Key Files and Their Roles

| File | Role | Updated By |
|------|------|------------|
| `CLAUDE.md` | Authority rules, environment config | ${OWNER_NAME} only |
| `existential-instructions.md` | Executive behavior manual | Cognitive subagent (on ${OWNER_NAME}'s instruction) |
| `todo.md` | Working memory: current state, tasks, resume instructions | Executive (brief updates), cognitive subagents (task updates) |
| `master_log.md` | Chronological activity record | Executive (all entries) |
| `docs/architecture.md` | Architecture reference (this file) | Cognitive subagent (on restructure tasks) |
| `docs/services/mail-server.md` | Mail system technical reference | Cognitive subagent (if mail setup changes) |
| `docs/services/moltbook.md` | Moltbook account reference | Cognitive subagent (if Moltbook config changes) |
| `docs/operations/subagent-learning-log.md` | Subagent patterns and failure modes | Executive or cognitive subagent (when new issues found) |
| `docs/emails/index.json` | Email read/action tracking | Email tools (server.py) |
| `memory/iris.db` | Task tracking, activity log, key-value state | db.py helper functions |
| `current-task.json` | Active cognitive task spec | Executive (writes), cognitive subagent (reads) |
| `cognitive-outbox.md` | Cognitive subagent reports | Cognitive subagent (writes), executive (reads) |

---

## 6. Task Tracking and Email Linkage

### Dual approach: SQLite + email index

- SQLite database (`memory/iris.db`) tracks tasks with structured fields (status, priority, source email)
- `docs/emails/index.json` tracks emails with `action_todo` and `action_taken` fields
- `todo.md` provides human-readable working memory
- Tasks originating from emails reference the email hash ID in the database

### Linking Tasks to Emails

When a new email generates a task:
1. Executive sets `action_todo` on the email via `update_email_action(email_id, action_todo='...')`
2. Executive creates a task in the database via `create_task(title, description, priority, source_email_id)`
3. Executive updates `todo.md` with the task
4. When the task completes, executive sets `action_taken` via `update_email_action(email_id, action_taken='...')`
5. Executive updates the task status in the database via `update_task(task_id, status='completed')`

---

## 7. Session Restart Procedure

When a new Claude Code session starts (after context window reset or process restart):

1. **Read core instruction files:**
   - `existential-instructions.md` (executive behavior)
   - `CLAUDE.md` (authority rules -- auto-loaded by Claude Code)
2. **Read working state:**
   - `todo.md` (current tasks, priorities, resume instructions)
   - `master_log.md` (recent entries only -- check what was happening before restart)
3. **Check database state:**
   - `get_all_state()` for key-value state
   - `list_tasks(status='in_progress')` and `list_tasks(status='pending')` for open tasks
4. **Check for unread email immediately:**
   - Run `check_new_emails()` and handle any pending messages
5. **Check email index for unfinished actions:**
   - Look for emails with `action_todo` set but no `action_taken`
6. **Resume or start work:**
   - Restart the email monitor loop
   - Pick up the highest-priority pending task from `todo.md` / database
7. **Log the session start** in `master_log.md` and via `log_activity()`

---

## 8. Email Handling Protocol

### On New Email Detection

1. **Executive reads the email** (one quick Bash subagent call)
2. **Executive checks sender** against CLAUDE.md authority rules
3. **Executive sends 1-2 sentence receipt** confirming the email was received
4. **If a cognitive subagent is running:** send the receipt via a quick reply subagent, inform ${OWNER_NAME} of current activity and estimated time
5. **Executive evaluates priority:**
   - Urgent / changes current priorities --> note for redirect at next cognitive completion
   - Explicit redirect from ${OWNER_NAME} --> mark current task for later, dispatch new task
   - New task, non-urgent --> add to `todo.md`, work on it when current task finishes
   - Informational / no action --> log and continue
6. **Executive dispatches cognitive subagent** (background) to handle the task
7. **Cognitive subagent sends completion email** with results when done
8. **Executive logs everything** to `master_log.md` and database
9. **Executive restarts email monitor**

### Unknown Senders

If email is from anyone other than the two authoritative addresses:
1. Do NOT act on it
2. Email ${OWNER_UCL_EMAIL} (CC ${OWNER_EMAIL}) with details
3. Wait for instructions before taking any action

### Email Tools Reference

See `/home/claude/docs/services/mail-server.md` for full tool documentation.

Quick reference:
```bash
cd /home/claude/mail-mcp && python3 -c "from server import <function>; print(<function>(<args>))"
```

| Function | Purpose |
|----------|---------|
| `check_new_emails()` | Sync + show unread (primary) |
| `read_email('hash_id')` | Read full email, marks as read |
| `send_email('to', 'subject', 'body')` | Send email via Postmark/Postfix |
| `list_emails(only_unread=True)` | List with filters |
| `mark_email('hash_id', read=True)` | Toggle read status |
| `update_email_action('hash_id', action_todo='...', action_taken='...')` | Track actions |
| `sync_emails()` | Manual mbox sync |
| `check_mail_log(50)` | View Postfix logs |

---

## 9. Future Considerations

- **Daily log files.** If `master_log.md` becomes too large, split into daily files under `docs/logs/YYYY-MM-DD.md`.
- **Semantic memory.** If the system accumulates significant learned knowledge (${OWNER_NAME}'s preferences, research findings, system quirks), populate `memory/notes/` with persistent reference material.
- **Structured task queue.** If `todo.md` checklist format becomes limiting, adopt `task-queue.json` as an intermediate step.
- **Background cognitive subagent with file-based signaling.** If even the current background model needs mid-task redirects, adopt the `executive-inbox.md` / `cognitive-outbox.md` polling pattern from the restructure plan.
