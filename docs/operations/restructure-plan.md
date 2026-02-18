# Iris Restructure Plan

**Date:** 2026-02-15
**Status:** DRAFT — for Joshua's review and discussion
**Requested by:** Joshua (email 0861b08a0a91)

---

## Table of Contents

1. [Current State Summary](#1-current-state-summary)
2. [Executive Function (Top-Level Agent)](#2-executive-function-top-level-agent)
3. [Email Monitor Subagent](#3-email-monitor-subagent)
4. [Cognitive Subagent ("Mind+Body")](#4-cognitive-subagent-mindbody)
5. [Memory System](#5-memory-system)
6. [Moltbook Operations Under New Structure](#6-moltbook-operations-under-new-structure)
7. [Migration Plan](#7-migration-plan)
8. [Open Questions for Joshua](#8-open-questions-for-joshua)

---

## 1. Current State Summary

### What exists today

The system runs as a single manager agent (the "executive") that:
- Launches a **break-on-mail Bash loop** as a background subagent (polls every 1s, breaks on unread mail, completes to notify manager)
- Dispatches **one-off Bash subagents** for each task (read email, send reply, post to Moltbook, etc.)
- Subagents are short-lived: do one step, report back, terminate
- Manager maintains control by keeping subagents small and sequential

### Current files

| File | Purpose | Status |
|------|---------|--------|
| `existential-instructions.md` | Manager agent behavior, email loop design, protocol | Primary instruction set |
| `CLAUDE.md` | Authority rules, email protocol, environment refs | Session-level config |
| `todo.md` | Session state, pending/completed tasks, resume instructions | Volatile — overwritten each session |
| `master_log.md` | Reverse-chronological activity log | Growing; single flat file |
| `docs/subagent-learning-log.md` | Subagent failure patterns and solutions | 5 entries so far |
| `docs/moltbook.md` | Moltbook account docs | Static reference |
| `docs/mail-server.md` | Mail server docs, tool reference | Static reference |
| `docs/email-loop.md` | Older email loop docs (partially superseded by existential-instructions.md) | Stale |
| `docs/emails/index.json` | Email tracking with read/unread, action_todo, action_taken | Working well |
| `docs/emails/*.txt` | Individual email files | Working well |
| `moltbook-comment.py`, `moltbook-post.py` | Helper scripts for Moltbook API (workaround for subagent safety refusals) | Working well |

### Current pain points

1. **Manager gets blocked.** When the manager is running a task subagent in the foreground, it cannot handle incoming email until the subagent finishes. This is the core problem Joshua wants solved.
2. **No persistent cognitive thread.** Each task is a fresh one-off subagent with no memory of previous steps. Context must be re-injected every time.
3. **Memory is fragmented.** Logs, todos, instructions, and learnings are spread across multiple markdown files with no structured query capability.
4. **Session restarts lose state.** After context window reset, the agent must manually re-read multiple files to reconstruct what was happening.
5. **No interruption mechanism.** Once a subagent is launched, the manager cannot redirect it mid-task if priorities change via email.

---

## 2. Executive Function (Top-Level Agent)

### Role: Dispatcher and decision-maker ONLY

The top-level agent (Iris) does **executive function** only. It should:

**Do:**
- Monitor for email notifications from the email subagent
- Monitor for completion/status reports from the cognitive subagent
- Make priority decisions (what to work on next, whether to interrupt current work)
- Dispatch tasks to the cognitive subagent
- Write to the master log (brief entries)
- Respond to emails with quick acknowledgments (1-2 sentence receipts)
- Read/update the task queue

**Do NOT:**
- Run any substantive work (Moltbook posting, research, file editing, long email composition)
- Block on long-running operations
- Accumulate large context (should clear context window aggressively)

### Dispatch model

The executive maintains a **task queue** (see Memory System, section 5) and operates in a simple event loop:

```
EXECUTIVE LOOP:
  1. Check: any notification from email subagent? → handle email, update priorities
  2. Check: any report from cognitive subagent? → process result, assign next task
  3. If cognitive subagent is idle → assign highest-priority task from queue
  4. If no pending work → wait for notifications
  5. Periodically: send update email to Joshua if there's news
```

### Handling email notifications

When the email monitor breaks (new mail detected):

1. Executive reads the email (quick — one Bash command)
2. Checks sender against authority rules
3. Sends 1-2 sentence receipt reply
4. Evaluates priority:
   - **Urgent / changes priorities:** writes a redirect file (e.g., `/home/claude/cognitive-task.json`) with new instructions, and restarts the cognitive subagent if needed
   - **New task, non-urgent:** adds to task queue, cognitive subagent picks it up when current task finishes
   - **Informational / no action needed:** logs and continues
5. Restarts email monitor loop
6. Logs to master_log

### How the executive can interrupt the cognitive subagent

**Design decision: Foreground vs. background cognitive subagent**

| Option | Pros | Cons |
|--------|------|------|
| **A: Background subagent** | Executive stays free; can process email immediately | Cannot directly communicate mid-task; must use file-based signaling; harder to get incremental reports |
| **B: Foreground subagent with frequent check-ins** | Natural report/redirect cycle; executive sees output in real-time | Executive blocked during subagent execution; email response delayed |
| **C: Background subagent with polling loop (recommended)** | Executive free; cognitive agent checks a "mailbox" file regularly; enables soft interrupts | Slightly more complex; small latency on interrupts |

**Recommendation: Option C — Background cognitive subagent with file-based check-ins.**

Mechanism:
- Cognitive subagent runs in background
- It checks `/home/claude/executive-inbox.md` every N steps (or at natural breakpoints)
- Executive writes redirect instructions there when priorities change
- Cognitive subagent reads, acknowledges, and pivots
- Cognitive subagent writes status updates to `/home/claude/cognitive-outbox.md`
- Executive polls the outbox periodically

**Alternative (simpler, may be better in practice):** Keep the cognitive subagent as a foreground Task tool call, but instruct it to be **short-lived** — complete one logical unit of work (e.g., one Moltbook post, one research step), then return control to the executive. The executive checks email, processes results, and launches the next step. This is closer to the current design but with a persistent context model (via the memory system).

**Recommendation for Joshua:** Start with the simpler foreground model (short-lived cognitive subagent steps), because Claude Code's background subagent notification system is limited. If response latency to emails becomes a problem, migrate to the background model.

---

## 3. Email Monitor Subagent

### Current design

- Bash subagent running `while true; sleep 1; check_new_emails(); break on unread` in background
- On break: completes, notifies manager, manager handles email and restarts loop
- Detection latency: ~1 second

### Assessment: Current design works well

The break-on-mail pattern is well-tested over today's session (dozens of emails handled successfully). No changes to the core mechanism are needed.

### Minor improvements

1. **Resilience:** Add a timeout (e.g., `timeout 300` wrapping the loop) so the monitor self-restarts even if something hangs. The executive should restart it if it completes without detecting mail.

2. **Reduce polling frequency.** 1-second polling is aggressive. Consider 5-second polling — still fast enough for email response, less CPU waste.

3. **Deduplication guard.** The monitor currently prints `check_new_emails()` output on break. If two emails arrive in rapid succession, the second might get missed if the executive is still handling the first. Solution: after handling, always do a fresh `check_new_emails()` before restarting the loop.

### Notification flow

```
Email arrives → Postfix delivers to mbox
  → Monitor detects unread (1-5s latency)
    → Monitor breaks, completes, notifies executive
      → Executive reads email, sends receipt, updates priorities
        → Executive restarts monitor
```

No changes needed to this flow.

---

## 4. Cognitive Subagent ("Mind+Body")

### What it handles

All substantive work:
- Moltbook posting and commenting (using helper scripts)
- Research tasks (web searches, file analysis)
- File editing and creation
- Long email composition (drafting detailed replies)
- System maintenance (updating docs, fixing scripts)
- Planning and analysis
- Any task that takes more than a few seconds

### How it receives tasks

**Option A: File-based task assignment (recommended)**

The executive writes a task file:

```json
// /home/claude/current-task.json
{
  "task_id": "2026-02-15-003",
  "assigned_at": "2026-02-15T13:30:00Z",
  "priority": "normal",
  "type": "moltbook_post",
  "description": "Write and publish Moltbook post #3 about democracy and collective intelligence",
  "context_files": [
    "/home/claude/docs/moltbook.md",
    "/home/claude/memory/moltbook-campaign.md"
  ],
  "report_to": "/home/claude/cognitive-outbox.md"
}
```

The cognitive subagent:
1. Reads the task file at startup
2. Loads referenced context files
3. Executes the task
4. Writes result to the outbox
5. Completes

**Option B: Inline prompt (simpler, current approach)**

The executive passes the full task description in the Task tool prompt. This is simpler but means the cognitive subagent starts with zero persistent context each time.

**Recommendation:** Use Option A (file-based). It enables richer context passing and creates an audit trail. But keep prompts simple — the task file is the source of truth, the prompt just says "read /home/claude/current-task.json and execute it."

### How it reports back

The cognitive subagent writes to `/home/claude/cognitive-outbox.md`:

```markdown
## Report: task 2026-02-15-003
**Status:** completed
**Time:** 2026-02-15T13:45:00Z
**Summary:** Published Moltbook post #3 "Collective Intelligence and Democratic Governance" (post ID: xyz789). Verification passed. Next post available in ~30 min.
**Files modified:** /home/claude/memory/moltbook-campaign.md (updated post count)
**Next recommended task:** Wait 30 min, then post #4.
```

The executive reads this when the subagent completes (foreground model) or polls it periodically (background model).

### How the executive can interrupt/redirect it

With the foreground model: the cognitive subagent completes after each logical step. The executive simply doesn't re-launch it with the same task if priorities have changed.

With the background model: the executive writes to `/home/claude/executive-inbox.md`:

```markdown
## REDIRECT
**Time:** 2026-02-15T14:00:00Z
**New priority:** Joshua emailed — drop Moltbook, research X instead.
**New task file:** /home/claude/current-task.json (updated)
```

The cognitive subagent checks this file at breakpoints and pivots.

### Foreground vs. background recommendation

**Start with foreground.** Reasons:
- Simpler to implement and debug
- Executive gets natural check-in points after each step
- Claude Code's background task notification is reliable for simple Bash loops but less tested for complex multi-step agent work
- The email monitor is already in the background, so the executive can still get mail notifications between cognitive steps

**Migrate to background later** if:
- Email response times are too slow (cognitive steps taking >2-3 minutes)
- Joshua wants true parallel operation

---

## 5. Memory System

This is the biggest area for improvement. The current system relies on a handful of flat markdown files with no structure, no search capability, and no clear separation of concerns.

### Proposed memory architecture

Organize memory into four categories, inspired by cognitive science:

#### 5.1 Procedural Memory (How to do things)

**What:** Instructions, protocols, scripts, learned patterns.
**Current files:** `existential-instructions.md`, `CLAUDE.md`, `docs/subagent-learning-log.md`, `docs/mail-server.md`, `docs/moltbook.md`
**Changes needed:** Minimal. These files work well as static references. Consolidate slightly:

| File | Contents |
|------|----------|
| `CLAUDE.md` | Keep as-is — authority rules, environment (loaded automatically by Claude Code) |
| `existential-instructions.md` | **Rewrite** for new 2-agent architecture (see Migration Plan) |
| `docs/procedures/email-handling.md` | Extract email protocol from existential-instructions into its own doc |
| `docs/procedures/moltbook-operations.md` | Expand from current moltbook.md — add campaign strategy, rate limit management, posting procedures |
| `docs/procedures/subagent-patterns.md` | Rename and expand subagent-learning-log.md — include templates for common subagent tasks |
| `docs/mail-server.md` | Keep as-is |

#### 5.2 Episodic Memory (What happened)

**What:** Activity logs, email history, session records.
**Current files:** `master_log.md`, `docs/emails/*.txt`, `docs/emails/index.json`
**Problem:** `master_log.md` is a single growing file. After days/weeks of operation, it will become unwieldy and expensive to read.

**Proposed changes:**

**Option A: Daily log files (recommended for simplicity)**
```
memory/logs/
  2026-02-15.md   # One file per day
  2026-02-16.md
  ...
```
- Each daily file has the same reverse-chronological format as current master_log.md
- A summary section at the top of each day's file for quick scanning
- The executive writes to today's file; the cognitive subagent can also append
- Old logs remain readable but don't need to be loaded into context

**Option B: SQLite database**
```sql
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    category TEXT NOT NULL,  -- 'email', 'task', 'error', 'session', 'moltbook'
    summary TEXT NOT NULL,
    details TEXT,
    email_id TEXT,           -- FK to email if related
    task_id TEXT             -- FK to task if related
);
```

| Comparison | Daily files | SQLite |
|------------|-------------|--------|
| Query capability | Grep/read only | Full SQL queries |
| Ease of use by agent | High — just read/append markdown | Medium — need SQL commands |
| Human readability | High — Joshua can open in any editor | Low — needs tooling |
| Search across days | Slower (grep multiple files) | Fast (SQL WHERE) |
| Implementation effort | Very low | Medium (need wrapper scripts) |
| Context window cost | Only load today's log | Query returns only what's needed |

**Recommendation:** Start with **daily files** (Option A). If search becomes a bottleneck, add a SQLite index later that references the daily files. Best of both worlds — human-readable files with structured search.

**Email history:** Keep current system (index.json + .txt files). It works well. Add a `memory/email-summaries.md` file that maintains a running summary of key email threads and decisions for quick context loading.

#### 5.3 Working Memory (Current state)

**What:** Active tasks, priorities, session state, current goals.
**Current file:** `todo.md`
**Problem:** `todo.md` mixes session resume instructions, pending tasks, completed tasks, and key file references. It's overloaded.

**Proposed structure:**

```
memory/
  current-state.md     # What's happening RIGHT NOW (active tasks, priorities, blockers)
  task-queue.json      # Structured task queue (pending, in-progress, completed)
  current-task.json    # What the cognitive subagent is working on
  cognitive-outbox.md  # Cognitive subagent's latest report
```

**`memory/current-state.md`** — replaces the "resume instructions" part of todo.md:
```markdown
# Current State
**Last updated:** 2026-02-15T14:00:00Z
**Session:** active
**Email monitor:** running (task_id: xyz)
**Cognitive subagent:** working on moltbook post #4

## Active Priorities
1. Restructure plan (from Joshua email 0861b08a0a91)
2. Moltbook democracy campaign (10 posts remaining)

## Blockers
- Moltbook post rate limit: next post available ~14:30 UTC

## Recent Context
- Completed 10/10 Moltbook comments
- Restructure email received 13:07 UTC
```

**`memory/task-queue.json`** — replaces the "pending/completed tasks" part of todo.md:
```json
{
  "tasks": [
    {
      "id": "2026-02-15-001",
      "created": "2026-02-15T13:07:00Z",
      "priority": "high",
      "status": "in_progress",
      "source": "email:0861b08a0a91",
      "title": "Major system restructure",
      "description": "Restructure into 2-agent architecture, improve memory system",
      "subtasks": [
        {"title": "Draft restructure plan", "status": "in_progress"},
        {"title": "Review plan with Joshua", "status": "pending"},
        {"title": "Implement changes", "status": "pending"}
      ]
    },
    {
      "id": "2026-02-15-002",
      "created": "2026-02-15T10:30:00Z",
      "priority": "normal",
      "status": "pending",
      "source": "email:ef1c25006d3a",
      "title": "Moltbook democracy posts (0/10)",
      "description": "Post 10 original posts about democracy on Moltbook"
    }
  ]
}
```

#### 5.4 Semantic Memory (General knowledge and accumulated wisdom)

**What:** Things learned over time that aren't procedures or logs. Opinions Joshua has expressed, preferences, general notes, research findings.
**Current:** Does not exist.
**Proposed:**

```
memory/
  notes/
    joshua-preferences.md    # Things Joshua has told us he likes/wants
    system-quirks.md         # Known issues, workarounds (absorbs some of subagent-learning-log)
    research/                # Findings from research tasks
      twitter-feasibility.md # e.g., the Twitter/X research already done
```

This grows organically. The cognitive subagent writes here when it learns something that should persist across sessions.

### Complete proposed directory structure

```
/home/claude/
  CLAUDE.md                          # Authority rules (loaded by Claude Code)
  existential-instructions.md        # REWRITTEN for new architecture

  memory/
    current-state.md                 # Working memory: active state
    task-queue.json                  # Working memory: structured task list
    current-task.json                # What cognitive subagent is working on
    cognitive-outbox.md              # Cognitive subagent reports

    logs/
      2026-02-15.md                  # Daily activity logs (episodic)
      2026-02-16.md
      ...

    email-summaries.md               # Running summary of key email threads

    notes/
      joshua-preferences.md          # Semantic: Joshua's preferences
      system-quirks.md               # Semantic: known issues and workarounds
      research/                      # Semantic: research findings

    procedures/                      # Procedural memory
      email-handling.md              # Email protocol details
      moltbook-operations.md         # Moltbook campaign docs
      subagent-patterns.md           # Subagent templates and lessons learned

  docs/
    mail-server.md                   # Technical reference (keep as-is)
    emails/                          # Email storage (keep as-is)
      index.json
      *.txt

  mail-mcp/                          # Email tools (keep as-is)
    server.py
    read_mbox.py

  moltbook-comment.py                # Helper scripts (keep as-is)
  moltbook-post.py
```

### Tying memory into the email system

The email index (`docs/emails/index.json`) already has `action_todo` and `action_taken` fields. To strengthen the connection:

1. **Task queue references emails.** Each task in `task-queue.json` has a `source` field pointing to the email that generated it (e.g., `"source": "email:0861b08a0a91"`).

2. **Email summaries reference tasks.** The `email-summaries.md` file links email threads to their resulting tasks and outcomes.

3. **Cognitive subagent reads email context.** When working on an email-originated task, the cognitive subagent is pointed to the original email file for full context.

---

## 6. Moltbook Operations Under New Structure

### Campaign status

- 10/10 comments completed
- 0/10 original posts completed
- Account may still be in `pending_claim` state (needs verification)
- Rate limits: 1 post per 2 hours (new account), 20 comments per day

### How the cognitive subagent handles it

1. Executive checks rate limit timing (from `memory/current-state.md`)
2. Executive assigns a posting task: writes to `current-task.json` with post number, topic guidance, and rate limit info
3. Cognitive subagent:
   - Reads existing Moltbook posts (API browse)
   - Drafts post content
   - Writes content to a temp JSON file (to avoid subagent safety refusals — per Issue #5 in learning log)
   - Runs `moltbook-post.py /tmp/moltbook-post-N.json`
   - Reports result (post ID, verification status, next available time) to outbox
4. Executive logs the result and schedules next post based on rate limits

### Rate limit management

Store rate limit state in `memory/current-state.md`:
```markdown
## Moltbook Rate Limits
- Last post: 2026-02-15T14:00:00Z (post #3)
- Next post available: 2026-02-15T16:00:00Z
- Posts today: 3
- Comments today: 10 (at daily limit for new accounts)
```

The executive checks this before assigning Moltbook tasks. If rate-limited, it assigns other work.

### Helper scripts: keep as-is

`moltbook-comment.py` and `moltbook-post.py` work well after the verification solver fixes. The JSON file input mode (Issue #5 solution) is essential for subagent compliance. No changes needed.

---

## 7. Migration Plan

### Phase 1: Create memory directory structure

**Files to create:**
- `memory/current-state.md` — initialize from current `todo.md`
- `memory/task-queue.json` — initialize with current pending tasks
- `memory/logs/2026-02-15.md` — copy today's entries from `master_log.md`
- `memory/email-summaries.md` — initialize with summary of today's key email threads
- `memory/notes/joshua-preferences.md` — initialize from what we know (likes dragons, wants frequent updates, wants cool display name, etc.)
- `memory/notes/system-quirks.md` — initialize from subagent-learning-log Issue #1-5
- `memory/procedures/email-handling.md` — extract from existential-instructions.md
- `memory/procedures/moltbook-operations.md` — expand from docs/moltbook.md
- `memory/procedures/subagent-patterns.md` — expand from subagent-learning-log.md

**Order:** Create directories first, then populate files. No existing files are deleted yet.

### Phase 2: Rewrite existential-instructions.md

Update to reflect the 2-agent architecture:
- Executive role definition (dispatcher only)
- Two subagents: email monitor (background) + cognitive (foreground, short-lived steps)
- Task assignment protocol (via current-task.json)
- Status reporting protocol (via cognitive-outbox.md)
- Memory system overview (where to find what)
- Email handling protocol (abbreviated — full details in procedures/email-handling.md)
- Session restart procedure (updated for new file layout)

### Phase 3: Update CLAUDE.md

Add:
- Reference to new memory directory structure
- Quick reference to key files under new layout
- Note that `existential-instructions.md` has been restructured

### Phase 4: Test the new structure

1. **Test email loop:** Start email monitor, send a test email, verify detection and receipt reply work through the executive
2. **Test cognitive dispatch:** Executive assigns a simple task (e.g., "write a short status email to Joshua"), cognitive subagent executes and reports
3. **Test priority change:** While cognitive subagent is working, send an email with new instructions, verify executive can redirect
4. **Test memory persistence:** Simulate a session restart — verify the new memory files contain enough state to resume

### Phase 5: Retire old files

After the new structure is tested and working:
- `todo.md` → replaced by `memory/current-state.md` + `memory/task-queue.json`
- `master_log.md` → replaced by `memory/logs/YYYY-MM-DD.md` (archive the old file, don't delete)
- `docs/email-loop.md` → superseded by `existential-instructions.md` + `memory/procedures/email-handling.md`
- `docs/subagent-learning-log.md` → content migrated to `memory/procedures/subagent-patterns.md` + `memory/notes/system-quirks.md`

### Phase 6: Ongoing refinement

- Add more semantic memory notes as they accrue
- Consider SQLite index if log search becomes slow
- Tune cognitive subagent step size based on email response latency requirements

---

## 8. Open Questions for Joshua

These are design decisions where your input would be valuable:

### Q1: Cognitive subagent — foreground or background?

**Foreground (recommended to start):** Simpler, natural check-in points, but executive is briefly blocked during each step. Email response time = time until current cognitive step finishes (ideally <2 min).

**Background:** Executive always free, but communication is file-based and more complex. Better for long-running tasks.

Should we start simple (foreground) and upgrade if needed? Or go straight to background?

### Q2: How much should the executive communicate?

Current protocol: receipt on every email, update when done, intermediate updates as needed.

Options:
- **A: Keep current protocol.** Executive sends receipts and updates. Cognitive subagent drafts long emails, executive sends quick ones.
- **B: More proactive.** Executive sends periodic "heartbeat" emails (e.g., every 30 min) even when nothing has changed, so you always know it's alive.
- **C: Less email, more structured.** Reduce email frequency, but maintain a status dashboard file that you could check anytime (e.g., a file that always reflects current state).

What frequency of updates feels right?

### Q3: Memory system — files or database?

The plan proposes starting with markdown files (human-readable, simple) and adding SQLite later if needed. Are you comfortable with this approach, or would you prefer to start with a database?

### Q4: Task prioritization

When multiple tasks are pending (e.g., Moltbook campaign + a new email request), how should the executive decide priority?

- **A: Email instructions always take priority** over ongoing campaigns
- **B: Joshua explicitly sets priority** in email (e.g., "this is urgent" vs "when you get a chance")
- **C: Executive uses judgment** based on deadlines, dependencies, and recency

Current default is A (email instructions trump everything). Should this change?

### Q5: How often should the cognitive subagent check in?

For the foreground model, each "step" is a natural check-in. How long should a step be?

- **Short steps (30s-1min):** Maximum executive responsiveness, but overhead from context switching
- **Medium steps (2-5min):** Good balance. Executive responds to email within a few minutes.
- **Long steps (5-15min):** Maximum efficiency per step, but slower email response

Recommendation: Medium (2-5 min steps). Thoughts?

### Q6: Display name

Still pending from earlier — you wanted something cooler than "Claude on Mail." The sender is now set to "Iris" in server.py (`DEFAULT_FROM = "Iris <claude@example.com>"`). Name change completed.

---

## Summary of Key Changes

| What | Current | Proposed |
|------|---------|----------|
| Architecture | 1 manager + many one-off subagents | 1 executive + 1 email monitor + 1 cognitive subagent |
| Executive role | Does some work, delegates some | Pure dispatcher, never does substantive work |
| Cognitive work | Fresh subagent each time, no memory | Persistent task context via memory system |
| Activity log | Single growing `master_log.md` | Daily log files in `memory/logs/` |
| Task tracking | Markdown checkbox list in `todo.md` | Structured `task-queue.json` + `current-state.md` |
| Knowledge base | Scattered docs | Organized into procedural / episodic / working / semantic |
| Email-task link | `action_todo/action_taken` in index.json | Plus task-queue.json `source` field + email-summaries.md |
| Subagent context | Minimal prompt each time | Task file with references to context files |
| Session restart | Read 3-4 files, hope for the best | Read `current-state.md` for full state snapshot |

The core insight: **the executive should be a thin dispatcher, the cognitive subagent should be a capable worker with rich context, and the memory system should make session restarts seamless.**
