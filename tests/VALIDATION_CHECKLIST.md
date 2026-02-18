# Iris + Wiggum Pre-Deployment Validation Checklist

This checklist must be completed before deploying the Iris + Wiggum architecture to production.

**Date:** _____________
**Validated by:** _____________
**Environment:** [ ] Development [ ] Production

---

## Phase 1: File Structure

### Core Files

- [ ] `/home/claude/iris/wiggum.sh` exists and is executable (`chmod +x`)
- [ ] `/home/claude/iris/prompts/iris.md` exists and is readable
- [ ] `/home/claude/iris/config/ai-wiggum.service` exists
- [ ] `/home/claude/iris/scripts/state/state_manager.py` exists
- [ ] `/home/claude/iris/scripts/state/db.py` exists
- [ ] `/home/claude/iris/scripts/mail/server.py` exists

### Worker Templates

- [ ] `/home/claude/iris/prompts/workers/research.md` exists
- [ ] `/home/claude/iris/prompts/workers/drafting.md` exists
- [ ] `/home/claude/iris/prompts/workers/moltbook.md` exists
- [ ] `/home/claude/iris/prompts/workers/coding.md` exists
- [ ] `/home/claude/iris/prompts/workers/analysis.md` exists
- [ ] `/home/claude/iris/prompts/workers/README.md` exists

### Test Files

- [ ] `/home/claude/iris/tests/test_wiggum.sh` exists and is executable
- [ ] `/home/claude/iris/tests/test_integration.sh` exists and is executable
- [ ] `/home/claude/iris/tests/test_state.py` exists and is executable
- [ ] `/home/claude/iris/tests/test_workers.sh` exists and is executable
- [ ] `/home/claude/iris/tests/test_email_flow.sh` exists and is executable
- [ ] `/home/claude/iris/tests/dry_run.sh` exists and is executable

---

## Phase 2: Configuration Validation

### Wiggum Configuration

- [ ] `wiggum.sh` contains infinite loop (`while true`)
- [ ] `wiggum.sh` checks for tmux session (`tmux has-session -t iris`)
- [ ] `wiggum.sh` spawns controller with correct prompt path
- [ ] `wiggum.sh` includes sleep interval (check every 10s)
- [ ] `wiggum.sh` uses correct Claude Code command

### Systemd Service

- [ ] Service file has correct `[Unit]` section
- [ ] Service file has correct `[Service]` section
- [ ] Service file has correct `[Install]` section
- [ ] `ExecStart` points to correct wiggum.sh path
- [ ] `User` is set correctly
- [ ] `Restart=always` is configured
- [ ] `WorkingDirectory` is set (if applicable)

### Prompt Configuration

- [ ] `iris.md` contains startup procedure
- [ ] `iris.md` contains main loop instructions
- [ ] `iris.md` contains email handling protocol
- [ ] `iris.md` contains voluntary exit procedure
- [ ] `iris.md` references correct file paths
- [ ] Worker templates are referenced correctly in `iris.md`

---

## Phase 3: Dependencies

### System Tools

- [ ] `tmux` is installed (`command -v tmux`)
- [ ] `python3` is installed (`python3 --version`)
- [ ] `claude-code` is installed (`command -v claude-code`)
- [ ] `bash` version 4.0+ (`bash --version`)

### Python Dependencies

- [ ] Python standard library available (json, os, tempfile, datetime)
- [ ] sqlite3 available for database operations
- [ ] No additional pip packages required (verify)

### File Permissions

- [ ] All scripts in `/home/claude/iris/tests/` are executable
- [ ] `wiggum.sh` is executable
- [ ] State directory writable (`/var/lib/ai-assistant/` or dev path)
- [ ] Log directory writable (if applicable)

---

## Phase 4: Database Validation

### Database Initialization

- [ ] Database file exists or can be created
- [ ] `tasks` table exists with correct schema
- [ ] `activity_log` table exists with correct schema
- [ ] `state` table exists with correct schema
- [ ] `sent_emails` table exists with correct schema
- [ ] Database indexes created

### Database Operations

- [ ] Can create tasks (`create_task()`)
- [ ] Can update tasks (`update_task()`)
- [ ] Can list tasks (`list_tasks()`)
- [ ] Can log activity (`log_activity()`)
- [ ] Can retrieve recent activity (`get_recent_activity()`)

Run: `python3 -c "import sys; sys.path.append('/home/claude/iris/scripts/state'); from db import *; print(list_tasks())"`

---

## Phase 5: State Management

### State File Operations

- [ ] Can initialize state (`initialize_state()`)
- [ ] Can save state (`save_state()`)
- [ ] Can load state (`load_state()`)
- [ ] Can merge state (`merge_state()`)
- [ ] Atomic writes work correctly (no temp files leaked)
- [ ] Corrupted file recovery works (returns empty dict)

### State Schema

- [ ] Schema version present
- [ ] `session` section complete
- [ ] `active_tasks` section complete
- [ ] `personality` section complete
- [ ] `recent_context` section complete
- [ ] `system` section complete

Run: `python3 /home/claude/iris/tests/test_state.py`

---

## Phase 6: Email Integration

### Email Tools

- [ ] Email server tools importable
- [ ] Can check for new emails (test with mock)
- [ ] Can send emails (test with mock)
- [ ] Can list emails
- [ ] Email tracking works (action_todo/action_taken)

### Email Protocols

- [ ] Authoritative sender list configured
- [ ] Unknown sender protocol documented
- [ ] Dragon response template ready
- [ ] Forward-to-Joshua logic documented
- [ ] Promise tracking protocol documented

Run: `./test_email_flow.sh`

---

## Phase 7: Test Suite Validation

### Unit Tests

- [ ] `test_wiggum.sh` passes (all tests)
- [ ] `test_state.py` passes (all tests)
- [ ] `test_workers.sh` passes (all tests)
- [ ] `test_email_flow.sh` passes (all tests)

### Integration Tests

- [ ] `test_integration.sh` passes (all tests)
- [ ] `test_integration.sh --dry` passes (dry run mode)

### Dry Run

- [ ] `dry_run.sh --once` completes without errors
- [ ] `dry_run.sh 60` runs for 60 seconds without crashes
- [ ] State persistence works in dry run
- [ ] No temp files leaked
- [ ] Resource usage acceptable

---

## Phase 8: Live System Testing

### Manual Wiggum Test

- [ ] Run `./wiggum.sh` manually (Ctrl+C after 30s)
- [ ] Verify tmux session created (`tmux ls`)
- [ ] Verify controller spawned in tmux
- [ ] Verify wiggum respawns controller when killed
- [ ] Verify logs show correct behavior

### Controller Lifecycle

- [ ] Controller starts successfully
- [ ] Controller loads state.json on startup
- [ ] Controller checks for emails
- [ ] Controller logs session start
- [ ] Controller can perform voluntary exit
- [ ] Wiggum respawns controller after exit

### State Persistence

- [ ] State file created on first run
- [ ] State persists across controller restarts
- [ ] Session count increments correctly
- [ ] Recent activity tracked correctly
- [ ] Personality notes preserved

---

## Phase 9: Production Readiness

### File Paths

- [ ] Update all paths from dev (`/home/claude/iris/`) to production (`/opt/ai-assistant/`)
- [ ] Update state.json path to production (`/var/lib/ai-assistant/state.json`)
- [ ] Update database path to production (if applicable)
- [ ] Update log paths to production (if applicable)

### Systemd Installation

- [ ] Service file copied to `/etc/systemd/system/`
- [ ] Service reloaded (`sudo systemctl daemon-reload`)
- [ ] Service enabled (`sudo systemctl enable ai-wiggum`)
- [ ] Service can start (`sudo systemctl start ai-wiggum`)
- [ ] Service status is active (`sudo systemctl status ai-wiggum`)

### Monitoring

- [ ] Can check service status (`systemctl status ai-wiggum`)
- [ ] Can view logs (`journalctl -u ai-wiggum -f`)
- [ ] Can attach to tmux session (`tmux attach -t iris`)
- [ ] State.json is being updated
- [ ] Database is being updated

---

## Phase 10: Security & Permissions

### File Ownership

- [ ] All files owned by correct user
- [ ] State file has appropriate permissions (600 or 644)
- [ ] Database file has appropriate permissions
- [ ] No world-writable files

### Email Security

- [ ] Email credentials secured (not in git)
- [ ] Only authorized senders can trigger actions
- [ ] Unknown sender protocol prevents abuse
- [ ] No hardcoded passwords in code

### Access Control

- [ ] Only authorized users can stop/start service
- [ ] Tmux session protected (user-owned)
- [ ] Database accessible only to service user

---

## Phase 11: Documentation

### User Documentation

- [ ] README.md exists and is current
- [ ] Architecture documented (DESIGN_NOTES.md or similar)
- [ ] Deployment instructions exist
- [ ] Troubleshooting guide available

### Code Documentation

- [ ] All Python modules have docstrings
- [ ] All bash scripts have header comments
- [ ] Complex logic has inline comments
- [ ] Worker templates have clear instructions

### Operational Documentation

- [ ] How to check system status
- [ ] How to restart controller
- [ ] How to read logs
- [ ] How to update prompts
- [ ] How to add new worker types

---

## Phase 12: Backup & Recovery

### Backup Procedures

- [ ] State.json backed up regularly
- [ ] Database backed up regularly
- [ ] Backup restoration tested
- [ ] Configuration files version controlled

### Recovery Testing

- [ ] Can recover from state.json corruption
- [ ] Can recover from database corruption
- [ ] Can recover from controller crash
- [ ] Can recover from full system restart

---

## Phase 13: Performance & Limits

### Resource Usage

- [ ] Memory usage acceptable (check with `top` or `htop`)
- [ ] CPU usage acceptable
- [ ] Disk space monitored
- [ ] No memory leaks detected (run for 24h test)

### Scale Testing

- [ ] Can handle multiple emails in queue
- [ ] Can handle multiple active tasks
- [ ] State file size remains manageable
- [ ] Database performance acceptable

---

## Final Sign-Off

### Pre-Deployment Checklist

- [ ] All tests pass
- [ ] Dry run successful
- [ ] Live testing successful
- [ ] Production paths configured
- [ ] Systemd service working
- [ ] Monitoring in place
- [ ] Documentation complete
- [ ] Backup procedures established

### Deployment Approval

**Deployed by:** _____________
**Date:** _____________
**Environment:** [ ] Development [ ] Production
**Commit/Version:** _____________

### Post-Deployment Verification

- [ ] Service running (`systemctl status ai-wiggum`)
- [ ] Controller active in tmux (`tmux ls`)
- [ ] State.json being updated
- [ ] Can receive and process test email
- [ ] Voluntary exit and respawn working
- [ ] Logs look healthy

---

## Troubleshooting Quick Reference

### Common Issues

**Controller won't start:**
- Check `journalctl -u ai-wiggum -f` for errors
- Verify iris.md exists and is readable
- Check claude-code is in PATH

**State not persisting:**
- Check state file permissions
- Check directory exists and is writable
- Review state_manager.py logs

**Email not working:**
- Test email tools separately
- Check credentials configuration
- Verify network connectivity

**Wiggum not respawning:**
- Check wiggum.sh syntax (`bash -n wiggum.sh`)
- Verify service restart policy
- Check systemd logs

### Support Contacts

- System administrator: _____________
- Developer: _____________
- Email: _____________

---

**Validation Complete:** [ ] Yes [ ] No

**Notes:**

_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
