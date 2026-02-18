# Iris + Wiggum - Directory Structure Documentation

This document provides detailed information about the directory structure, file purposes, and implementation status.

## Root Level

### /home/claude/iris/

Main directory for Iris + Wiggum architecture.

| File | Purpose | Status | Next Steps |
|------|---------|--------|------------|
| `README.md` | Overview and quick reference | ✅ Complete | - |
| `STRUCTURE.md` | This file - structure documentation | ✅ Complete | - |
| `revised-architecture.md` | Complete architecture specification | ✅ Complete | Reference for implementation |
| `wiggum.sh` | Controller respawn loop | 🟡 Skeleton | Implement main loop logic (lines 86-104 in arch doc) |

### Legacy from previous work:
| Directory | Purpose | Status |
|-----------|---------|--------|
| `email/` | Previous architecture attempt | ✅ Kept for reference | Contains docs and scripts from yesterday |

## Prompts Directory

### /home/claude/iris/prompts/

Controller and worker prompt storage.

| File | Purpose | Status | Next Steps |
|------|---------|--------|------------|
| `iris.md` | Main controller prompt (existential instructions) | ✅ Complete | Ready for integration testing |

**Controller Prompt (iris.md):**
- Full implementation of controller lifecycle and behavior
- Startup procedure with state restoration
- Main loop with email monitoring and task processing
- Email handling protocol (authority rules, unknown senders, promise tracking)
- Worker subagent orchestration
- Context self-assessment and voluntary exit procedure
- State management with continuous checkpointing
- Personality continuity across restarts
- Complete tool reference and error handling

### /home/claude/iris/prompts/workers/

Worker subagent prompt templates.

| File | Purpose | Status | Next Steps |
|------|---------|--------|------------|
| `README.md` | Worker template documentation | ✅ Complete | - |
| `research.md` | Research and information gathering worker | ✅ Complete | Ready for use |
| `drafting.md` | Email, document, and report writing worker | ✅ Complete | Ready for use |
| `moltbook.md` | Moltbook posting and commenting worker | ✅ Complete | Ready for use |
| `coding.md` | Code writing, modification, and refactoring worker | ✅ Complete | Ready for use |
| `analysis.md` | Data processing and analysis worker | ✅ Complete | Ready for use |

**Worker Templates:**

Each template includes:
- Specialized role and purpose
- Input expectations from controller
- Available tools and utilities
- Step-by-step process workflow
- Structured output format
- Task-specific guidelines and patterns
- Checkpointing for long-running tasks
- Error handling and recovery
- Example tasks and outputs

**Worker Types:**
- **research.md**: Web search, literature review, fact-finding (2-10 min tasks)
- **drafting.md**: Emails, documents, reports, unknown sender responses (2-8 min tasks)
- **moltbook.md**: Posts/comments with rate limit awareness (2-5 min tasks, JSON file input method)
- **coding.md**: Implementation, bug fixes, refactoring (5-15 min tasks)
- **analysis.md**: Descriptive, comparative, trend analysis (3-12 min tasks)

## Scripts Directory

### /home/claude/iris/scripts/mail/

Email handling tools.

| File | Purpose | Source | Status |
|------|---------|--------|--------|
| `server.py` | MCP email server (18KB, 653 lines) | Copied from ~/mail-mcp/ | ✅ Ready to use |
| `read_mbox.py` | Mbox reader utility | Copied from ~/mail-mcp/ | ✅ Ready to use |

**Functions available:**
- `check_new_emails()` - Sync mailbox and show unread
- `read_email(hash_id)` - Read specific email (marks as read)
- `send_email(to, subject, body)` - Send email
- `list_emails(only_unread=True)` - List emails with filters

**Usage from controller:**
```python
import sys
sys.path.append('/home/claude/iris/scripts/mail')
from server import check_new_emails, read_email, send_email
```

### /home/claude/iris/scripts/state/

State and database management.

| File | Purpose | Source | Status |
|------|---------|--------|--------|
| `db.py` | Database helper module (416 lines) | Copied from ~/memory/ | ✅ Ready to use |

**Database:** /home/claude/memory/iris.db (shared with live system)

**Tables:**
- `tasks` - Task tracking (id, status, priority, title, description, result)
- `activity_log` - Event log (timestamp, category, summary, details)
- `state` - Key-value store
- `sent_emails` - Outgoing email archive

**Functions available:**
```python
# Tasks
create_task(title, description, priority, source_email_id)
update_task(task_id, status=..., result=...)
get_task(task_id)
list_tasks(status=None, priority=None)

# Activity log
log_activity(category, summary, details, email_id, task_id)
get_recent_activity(limit=20, category=None)

# State (key-value)
set_state(key, value)
get_state(key)
get_all_state()

# Sent emails
log_sent_email(to_addr, from_addr, subject, body, message_id, in_reply_to)
get_sent_emails(to_addr=None, limit=20)
get_email_thread(email_address, subject_match, limit=50)
```

### /home/claude/iris/scripts/health/

Monitoring and resource management.

| Status | Next Steps |
|--------|------------|
| ⏸️ Placeholder | Phase 2: Create health monitor for resource limits, alerts, cleanup |

**Future tools:**
- Resource monitor (kill processes > 3GB RAM)
- Disk usage monitor
- Alert system for operator
- Log cleanup utilities

## Config Directory

### /home/claude/iris/config/

System service configurations.

| File | Purpose | Status | Next Steps |
|------|---------|--------|------------|
| `ai-wiggum.service` | Systemd service template | 🟡 Skeleton | Update ExecStart path when wiggum.sh complete, test installation |

**Installation (Phase 4):**
```bash
sudo cp config/ai-wiggum.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-wiggum
sudo systemctl start ai-wiggum
```

## Tests Directory

### /home/claude/iris/tests/

Testing and validation.

| Status | Next Steps |
|--------|------------|
| ⏸️ Placeholder | Phase 4: Create test suite for crash recovery, state persistence, email handling, worker spawning |

**Future tests:**
- Crash recovery (kill controller, verify respawn)
- Voluntary exit (trigger context refresh, check state continuity)
- State persistence (verify state.json correctness across restart)
- Email handling (test ack, triage, unknown sender protocol)
- Worker spawning (test background task execution)

## State Files (Future)

These will be created during Phase 2 implementation:

### /var/lib/ai-assistant/ (or ~/iris/ initially)

| File/Dir | Purpose | Status |
|----------|---------|--------|
| `state.json` | Controller's external memory | ⏸️ To be created | Phase 2: Define schema (lines 329-389 in arch doc) |
| `tasks/{id}/` | Per-task working directories | ⏸️ To be created | Phase 3: Worker checkpoint storage |

### /home/claude/

| File | Purpose | Status |
|------|---------|--------|
| `master_log.md` | Human-readable activity log | ⏸️ To be created | Phase 2: Reverse-chronological markdown log |

## Implementation Status Legend

- ✅ **Complete** - File exists and ready to use
- 🟡 **Skeleton** - File exists with structure but needs implementation
- ⏸️ **Placeholder** - Directory exists or planned but empty
- ❌ **Blocked** - Waiting on dependencies

## File Size Summary

**Total structure created:**
- Directories: 8
- Files: 11 (4 skeleton, 4 complete, 3 copied tools)

**Copied tools:**
- `scripts/mail/server.py` - 18KB (653 lines)
- `scripts/mail/read_mbox.py` - 2KB (79 lines)
- `scripts/state/db.py` - 14KB (416 lines)

**Documentation:**
- `revised-architecture.md` - 30KB (complete architecture)
- `README.md` - 5KB (overview)
- `STRUCTURE.md` - This file

## Integration Points

### With Live System

**Current directories that will be used:**
- Database: /home/claude/memory/iris.db (shared)
- Email storage: /home/claude/docs/emails/ (shared)
- Email index: /home/claude/docs/emails/index.json (shared)

**New directories for Iris + Wiggum:**
- Controller state: ~/iris/state.json
- Task checkpoints: ~/iris/tasks/ (or /var/lib/ai-assistant/)
- Activity log: ~/master_log.md

### With System Services

**After Phase 4 deployment:**
- Systemd manages: ai-wiggum.service
- Tmux session: iris
- Logs: journalctl -u ai-wiggum
- User: claude (non-root)

## Phase Breakdown

### Phase 1: Structure (CURRENT - COMPLETE)
- ✅ Directory structure created
- ✅ Skeleton files with //todocodehere
- ✅ Tools copied from live system
- ✅ Documentation in place

### Phase 2: Core Implementation (COMPLETE)
- ✅ Implement wiggum.sh loop
- ✅ Implement state.json schema (state_manager.py)
- ✅ Implement state management utilities

### Phase 3: Controller and Worker Prompts (COMPLETE)
- ✅ Implement iris.md controller prompt (full instructions)
- ✅ Create worker prompt templates (5 templates)
  - ✅ research.md - Research and information gathering
  - ✅ drafting.md - Writing and document creation
  - ✅ moltbook.md - Moltbook posting with rate limits
  - ✅ coding.md - Code writing and modification
  - ✅ analysis.md - Data processing and analysis

### Phase 4: Integration & Testing
- ⏸️ Full system integration test
- ⏸️ Email monitoring validation (watchdog or poll)
- ⏸️ Worker orchestration testing
- ⏸️ State persistence across crash/voluntary exit
- ⏸️ Unknown sender protocol validation
- ⏸️ Resource monitoring implementation

### Phase 5: Deployment
- ⏸️ Systemd service installation
- ⏸️ Production configuration (/var/lib/ai-assistant/)
- ⏸️ Monitoring and alerting
- ⏸️ Operator documentation

## References

All implementation details are documented in **revised-architecture.md**.

Key sections by line number:
- Wiggum loop: lines 86-104, 106-123
- Controller lifecycle: lines 161-204
- Email handling: lines 436-512
- Worker subagents: lines 248-287
- State management: lines 329-416
- Voluntary exit: lines 289-327

## TODOs by File

### wiggum.sh
- [ ] Implement main while loop
- [ ] Add tmux session detection
- [ ] Add controller spawn logic
- [ ] Add logging
- [ ] Make executable (chmod +x)

### prompts/iris.md
- [x] Implement startup procedure
- [x] Implement main loop logic
- [x] Implement email handling protocol
- [x] Implement worker spawning
- [x] Implement context self-assessment
- [x] Implement voluntary exit procedure
- [x] Define state.json read/write logic

### config/ai-wiggum.service
- [x] Update ExecStart path after wiggum.sh complete
- [ ] Test service installation
- [ ] Verify resource limits
- [ ] Test restart behavior

### prompts/workers/
- [x] Create research.md template
- [x] Create drafting.md template
- [x] Create moltbook.md template
- [x] Create coding.md template
- [x] Create analysis.md template
- [ ] Create debug.md template (future, optional)

### State management
- [x] Create state.json schema
- [x] Implement state load/save utilities
- [ ] Create master_log.md format (Phase 4)
- [ ] Set up task checkpoint directories (Phase 4)

---

**Last updated:** 2026-02-16
**Phase:** 3 (Controller + Worker Prompts) - Complete
**Next:** Phase 4 - Integration & Testing
