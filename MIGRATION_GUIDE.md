# Migration Guide: Current Iris → Iris + Wiggum

**Version:** 1.0
**Date:** February 16, 2026

This guide helps you migrate from the current Iris implementation to the new Iris + Wiggum architecture with minimal disruption.

---

## Table of Contents

1. [Migration Overview](#migration-overview)
2. [Pre-Migration Checklist](#pre-migration-checklist)
3. [State Export from Current System](#state-export-from-current-system)
4. [Parallel Operation Period](#parallel-operation-period)
5. [Cutover Procedure](#cutover-procedure)
6. [Post-Migration Validation](#post-migration-validation)
7. [Troubleshooting Migration Issues](#troubleshooting-migration-issues)

---

## Migration Overview

### What's Changing

**Architecture:**
- **Old:** Single long-running Claude Code instance
- **New:** Wiggum loop + voluntary context clearing controller

**State Management:**
- **Old:** Ad-hoc state files, in-context memory
- **New:** Structured state.json + SQLite database

**Recovery:**
- **Old:** Manual restart after crash
- **New:** Automatic respawn via systemd + wiggum loop

**File Locations:**
- **Old:** Mixed locations (~/, ~/docs/, etc.)
- **New:** Organized structure (/opt/ai-assistant/, /var/lib/ai-assistant/)

### What's Staying the Same

**Personality:**
- Same "I'm Iris" identity
- Same email-driven workflow
- Same dragon-themed humor for unknown senders
- Same relationship with Joshua

**Data:**
- Email history (preserved in database)
- Task history (migrated to new schema)
- Master log (continuous)
- Email storage (unchanged)

**Capabilities:**
- Email monitoring
- Task execution
- Worker spawning
- Report generation
- Service integrations (Moltbook, Prolific, etc.)

---

## Pre-Migration Checklist

### 1. Document Current State

```bash
# Save current system state
mkdir -p ~/iris_migration_backup/$(date +%Y%m%d)
cd ~/iris_migration_backup/$(date +%Y%m%d)

# Capture current running state
ps aux | grep claude > running_processes.txt
tmux ls > tmux_sessions.txt 2>&1 || echo "No tmux sessions"

# Document active tasks
# (If current Iris has a task list, export it)
```

### 2. Export Current Data

**Email Database:**
```bash
# Backup email database
cp ~/memory/iris.db ~/iris_migration_backup/$(date +%Y%m%d)/iris.db.backup

# Export as SQL dump
sqlite3 ~/memory/iris.db .dump > ~/iris_migration_backup/$(date +%Y%m%d)/iris.db.sql
```

**State Files:**
```bash
# Find and backup any state files
find ~ -name "state*.json" -o -name "iris_state*" -o -name "context*" 2>/dev/null | \
  xargs -I {} cp {} ~/iris_migration_backup/$(date +%Y%m%d)/

# Backup master log
cp ~/master_log.md ~/iris_migration_backup/$(date +%Y%m%d)/ 2>/dev/null || echo "No master log"
```

**Email Storage:**
```bash
# Backup email storage
tar czf ~/iris_migration_backup/$(date +%Y%m%d)/emails.tar.gz ~/docs/emails/ 2>/dev/null
```

### 3. Document Active Tasks

Create a manual task list:

```bash
cat > ~/iris_migration_backup/$(date +%Y%m%d)/active_tasks.md << 'EOF'
# Active Tasks at Migration

## In Progress
- [ ] Task 1: [description]
- [ ] Task 2: [description]

## Pending
- [ ] Task 3: [description]

## Waiting For
- [ ] Task 4: [waiting for what]

## Notes
[Any important context about current work]
EOF

# Edit this file manually
nano ~/iris_migration_backup/$(date +%Y%m%d)/active_tasks.md
```

### 4. Notify Joshua (Optional)

If migration will cause brief downtime:

```bash
mail -s "[Iris] Migration Scheduled" owner-work@example.com << 'EOF'
Hello Joshua,

I'm preparing to migrate to the new Iris + Wiggum architecture.

Migration scheduled: [date/time]
Expected downtime: ~15 minutes
Parallel testing period: [duration]

During migration:
- Email monitoring will continue
- Some tasks may be delayed
- All data will be preserved

I'll send confirmation when complete.

-- Iris
EOF
```

### 5. Test New System

```bash
# Run all tests on new system
cd ~/iris/tests
./run_all_tests.sh

# All tests must pass before migration
```

### 6. Create Rollback Plan

Document rollback steps:

```bash
cat > ~/iris_migration_backup/$(date +%Y%m%d)/ROLLBACK.md << 'EOF'
# Rollback Plan

If migration fails:

1. Stop new system:
   sudo systemctl stop ai-wiggum
   tmux kill-session -t iris

2. Restore backups:
   cp ~/iris_migration_backup/YYYYMMDD/iris.db.backup ~/memory/iris.db
   cp ~/iris_migration_backup/YYYYMMDD/master_log.md ~/master_log.md

3. Restart old system:
   [Document how to restart current Iris]

4. Verify:
   [Document verification steps]

5. Notify Joshua of rollback
EOF
```

---

## State Export from Current System

### 1. Extract Recent Context

If current Iris has any form of state, export it:

```bash
# Create state export script
cat > ~/iris_migration_backup/export_state.py << 'EOF'
#!/usr/bin/env python3
"""Export current Iris state to new format."""

import json
import sqlite3
from datetime import datetime

def export_current_state():
    """Export current system state to new state.json format."""

    state = {
        "last_session_end": None,
        "exit_reason": "migration_from_old_system",
        "personality": {
            "name": "Iris",
            "identity": "AI assistant for Joshua",
            "awareness": "Migrating to new Iris + Wiggum architecture",
            "recent_tone": "Professional, helpful",
            "relationship_notes": "Continuous service, same personality"
        },
        "active_tasks": [],
        "recent_context": {
            "last_email": None,
            "last_action": "Preparing for migration to new architecture",
            "waiting_for": "Migration completion"
        },
        "task_queue": {
            "total_pending": 0,
            "highest_priority": None,
            "queue_snapshot": []
        },
        "self_notes": [
            "Migrated from original Iris to Iris + Wiggum architecture",
            "Email response protocol: ack immediately, update on completion",
            "Unknown senders get dragon-themed response + forward to Joshua",
            "Joshua prefers CSV format for data outputs",
            "Always email results when tasks complete"
        ],
        "statistics": {
            "total_sessions": 0,  # Reset for new architecture
            "tasks_completed_today": 0,
            "context_refreshes_today": 0,
            "last_error": None
        }
    }

    # Try to extract data from database
    try:
        conn = sqlite3.connect(f"{os.path.expanduser('~')}/memory/iris.db")
        cursor = conn.cursor()

        # Get recent tasks
        cursor.execute("""
            SELECT id, title, description, status, priority
            FROM tasks
            WHERE status IN ('pending', 'in_progress')
            ORDER BY priority DESC, created_at DESC
            LIMIT 10
        """)

        for row in cursor.fetchall():
            task = {
                "task_id": row[0],
                "description": f"{row[1]}: {row[2]}",
                "status": row[3],
                "priority": row[4],
                "progress": "Pending migration",
                "next_steps": ["Resume after migration"],
                "worker_id": None,
                "started_at": None
            }

            if task["status"] == "in_progress":
                state["active_tasks"].append(task)
            else:
                state["task_queue"]["queue_snapshot"].append(task)

        state["task_queue"]["total_pending"] = len(state["task_queue"]["queue_snapshot"])

        # Get most recent email
        cursor.execute("""
            SELECT sender, subject, timestamp
            FROM emails
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        email_row = cursor.fetchone()
        if email_row:
            state["recent_context"]["last_email"] = {
                "from": email_row[0],
                "subject": email_row[1],
                "summary": "Last email before migration",
                "timestamp": email_row[2]
            }

        conn.close()

    except Exception as e:
        print(f"Warning: Could not extract from database: {e}")

    return state

if __name__ == "__main__":
    import os

    state = export_current_state()

    # Save to migration backup
    backup_dir = f"{os.path.expanduser('~')}/iris_migration_backup"
    date_dir = datetime.now().strftime("%Y%m%d")
    output_file = f"{backup_dir}/{date_dir}/exported_state.json"

    os.makedirs(f"{backup_dir}/{date_dir}", exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(state, f, indent=2)

    print(f"✓ State exported to: {output_file}")
    print(f"✓ Active tasks: {len(state['active_tasks'])}")
    print(f"✓ Pending tasks: {state['task_queue']['total_pending']}")
EOF

chmod +x ~/iris_migration_backup/export_state.py

# Run export
python3 ~/iris_migration_backup/export_state.py
```

### 2. Document Learnings and Preferences

Manually document what current Iris has learned:

```bash
cat > ~/iris_migration_backup/$(date +%Y%m%d)/learnings.md << 'EOF'
# Iris Learnings (to migrate)

## Joshua's Preferences
- [Document preferences learned]
- Email format preferences
- Output format preferences
- Response timing preferences

## Service-Specific Notes
- Moltbook: [rate limits, posting patterns]
- Prolific: [data format preferences]
- GitHub: [workflow preferences]

## Communication Style
- [Tone preferences]
- [Humor guidelines]
- [Update frequency]

## Task Patterns
- [Common task types]
- [Typical workflows]
- [Success criteria]

## Error Learnings
- [Things to avoid]
- [Known issues]
- [Workarounds]
EOF

# Edit this file manually
nano ~/iris_migration_backup/$(date +%Y%m%d)/learnings.md
```

### 3. Transfer to New State Format

```bash
# Copy exported state to new system's initial state
cp ~/iris_migration_backup/$(date +%Y%m%d)/exported_state.json \
   ~/iris/state.json

# Manually add learnings to state.json
nano ~/iris/state.json
# Add items from learnings.md to "self_notes" section
```

---

## Parallel Operation Period

Run both systems in parallel for testing before full cutover.

### 1. Keep Old System Running

```bash
# Document how current Iris is running
ps aux | grep iris
tmux ls

# Don't stop current system yet
```

### 2. Start New System in Test Mode

```bash
# Start new system with different tmux session name
cd ~/iris

# Edit wiggum.sh temporarily to use different session name
sed 's/tmux new-session -d -s iris/tmux new-session -d -s iris-new/' wiggum.sh > /tmp/wiggum_test.sh
chmod +x /tmp/wiggum_test.sh

# Start test instance
/tmp/wiggum_test.sh &

# Verify it starts
sleep 5
tmux ls
# Should see both: iris (old) and iris-new (new)
```

### 3. Test New System

```bash
# Attach to new system
tmux attach -t iris-new

# Watch it initialize
# Verify it loads state.json
# Check for errors

# Detach: Ctrl-B, then D
```

### 4. Send Test Email to New System

This requires temporarily routing test emails to new system, or manually triggering:

```bash
# Option A: Send test email and process manually
# 1. Send test email as normal
# 2. Attach to iris-new tmux session
# 3. Manually trigger email check if needed

# Option B: Create test state file with fake email
tmux attach -t iris-new
# In session, manually type:
# "Check for new email and report status"
```

### 5. Compare Behavior

Monitor both systems:

```bash
# Terminal 1: Watch old system
tmux attach -t iris

# Terminal 2: Watch new system
tmux attach -t iris-new

# Terminal 3: Monitor logs
journalctl -f
```

### 6. Test Key Workflows

For new system, test:

- [ ] Email detection
- [ ] Email acknowledgment
- [ ] Task queuing
- [ ] Worker spawning
- [ ] Task completion
- [ ] State persistence
- [ ] Voluntary exit
- [ ] Crash recovery (kill and respawn)
- [ ] Unknown sender protocol

### 7. Parallel Run Duration

Recommended: **24-48 hours** of parallel operation

This allows:
- Multiple email cycles
- Multiple voluntary exits
- Full task workflows
- Observation of memory usage
- Detection of edge cases

---

## Cutover Procedure

When confident in new system, perform cutover.

### 1. Choose Cutover Window

**Recommended:** Low-activity period (evening/weekend)

**Announce cutover:**

```bash
mail -s "[Iris] Migration Starting" owner-work@example.com << 'EOF'
Hello Joshua,

Beginning migration to Iris + Wiggum architecture now.

Expected duration: 15 minutes
Downtime: Minimal (brief email processing delay)

Will confirm when complete.

-- Iris
EOF
```

### 2. Pause Old System

```bash
# Stop old system gracefully
# (Method depends on how current Iris runs)

# If in tmux:
tmux attach -t iris
# Send shutdown command or Ctrl-C

# If as systemd service:
sudo systemctl stop [old-iris-service]

# Verify stopped
ps aux | grep iris
```

### 3. Final State Sync

```bash
# Export final state from old system
python3 ~/iris_migration_backup/export_state.py

# Copy to new system
cp ~/iris_migration_backup/$(date +%Y%m%d)/exported_state.json \
   /var/lib/ai-assistant/state.json

# Verify
cat /var/lib/ai-assistant/state.json | jq .
```

### 4. Start New System as Primary

```bash
# Stop test instance (if running)
tmux kill-session -t iris-new 2>/dev/null

# Deploy to production (follow DEPLOYMENT_GUIDE.md)
# Or if already deployed, just start:
sudo systemctl start ai-wiggum

# Verify started
systemctl status ai-wiggum
tmux ls | grep iris
```

### 5. Immediate Verification

```bash
# Attach and watch startup
tmux attach -t iris

# Verify:
# - Loads state.json
# - Starts email monitoring
# - No errors
# - Initializes correctly

# Detach: Ctrl-B, then D
```

### 6. Send Test Email

```bash
mail -s "Test: Post-migration verification" claude@mail.example.com << 'EOF'
Hello Iris,

Verify you're running on new architecture.

Please acknowledge and report status.

Joshua
EOF
```

**Expected:** Acknowledgment within 10 seconds

### 7. Monitor for First Hour

```bash
# Watch logs
journalctl -u ai-wiggum -f

# Check state updates
watch -n 10 'stat /var/lib/ai-assistant/state.json | grep Modify'

# Monitor resources
watch -n 5 'ps aux | grep -E "wiggum|claude-code" | grep -v grep'
```

### 8. Confirm Cutover Complete

```bash
mail -s "[Iris] Migration Complete" owner-work@example.com << 'EOF'
Hello Joshua,

Migration to Iris + Wiggum architecture is complete.

Status: ✓ Running on new system
Email monitoring: ✓ Active
State persistence: ✓ Working
All tests: ✓ Passed

I'm the same Iris, just with improved stability architecture.

-- Iris
EOF
```

---

## Post-Migration Validation

### First 24 Hours

**Checklist:**

- [ ] Email monitoring working
- [ ] Tasks being processed
- [ ] Acknowledgments sent
- [ ] Results emailed
- [ ] State file updating
- [ ] No crashes
- [ ] Voluntary exit working
- [ ] Resource usage normal
- [ ] Logs clean

**Actions:**

```bash
# Run health check every hour
watch -n 3600 '/opt/ai-assistant/scripts/health/health_check.sh'

# Monitor logs continuously
journalctl -u ai-wiggum -f

# Check state file
watch -n 300 'cat /var/lib/ai-assistant/state.json | jq .statistics'
```

### First Week

**Test all workflows:**

1. **Email workflows:**
   - [ ] Simple task (direct handling)
   - [ ] Complex task (worker spawning)
   - [ ] Multi-step task
   - [ ] Unknown sender (dragon response)

2. **System resilience:**
   - [ ] Voluntary exit/restart cycle
   - [ ] Crash recovery (kill controller, verify respawn)
   - [ ] State persistence across restarts
   - [ ] Long-running task handling

3. **Integration points:**
   - [ ] Database writes
   - [ ] Email sending
   - [ ] Worker subagent spawning
   - [ ] Master log updates

### Compare Metrics

**Old System vs New System:**

| Metric | Old System | New System | Status |
|--------|-----------|------------|--------|
| Email response time | [baseline] | [measure] | [ ] OK |
| Task completion rate | [baseline] | [measure] | [ ] OK |
| Uptime | [baseline] | [measure] | [ ] OK |
| Memory usage | [baseline] | [measure] | [ ] OK |
| Crash frequency | [baseline] | [measure] | [ ] OK |

### Verify Data Integrity

```bash
# Check database integrity
sqlite3 ~/memory/iris.db "PRAGMA integrity_check;"

# Count records
sqlite3 ~/memory/iris.db << 'EOF'
SELECT 'Emails:', COUNT(*) FROM emails;
SELECT 'Tasks:', COUNT(*) FROM tasks;
SELECT 'Activity log:', COUNT(*) FROM activity_log;
EOF

# Compare with pre-migration counts
# (from backup: ~/iris_migration_backup/YYYYMMDD/iris.db.backup)
```

### Verify State Continuity

```bash
# Check that personality and learnings transferred
cat /var/lib/ai-assistant/state.json | jq '.personality'
cat /var/lib/ai-assistant/state.json | jq '.self_notes'

# Should contain:
# - Same identity ("Iris")
# - Migrated learnings
# - Joshua's preferences
```

### User Experience Check

Email Joshua for feedback:

```bash
mail -s "[Iris] Migration Feedback Request" owner-work@example.com << 'EOF'
Hello Joshua,

One week post-migration status report:

Migration date: [date]
Uptime: 7 days
Tasks completed: [count]
Voluntary refreshes: [count]
Crashes: [count]

From your perspective, have you noticed:
- Any difference in response time?
- Any issues or errors?
- Any changes in behavior?

Please let me know if you've experienced any problems.

-- Iris
EOF
```

---

## Troubleshooting Migration Issues

### Issue: Lost State During Migration

**Symptoms:** New system doesn't have context from old system

**Solution:**

```bash
# Restore exported state
cp ~/iris_migration_backup/$(date +%Y%m%d)/exported_state.json \
   /var/lib/ai-assistant/state.json

# Restart controller
sudo systemctl restart ai-wiggum

# Verify state loaded
tmux attach -t iris
```

### Issue: Database Not Accessible

**Symptoms:** New system can't read database

**Solution:**

```bash
# Check database location
ls -l ~/memory/iris.db

# Check permissions
chmod 644 ~/memory/iris.db

# Test connection
cd /opt/ai-assistant/scripts/state
python3 -c "from db import get_connection; conn = get_connection(); print('✓ Connected')"

# If database missing, restore backup
cp ~/iris_migration_backup/YYYYMMDD/iris.db.backup ~/memory/iris.db
```

### Issue: Emails Not Being Processed

**Symptoms:** New system not detecting emails

**Solution:**

```bash
# Test email tools
cd /opt/ai-assistant/scripts/mail
python3 -c "from server import check_new_emails; print(check_new_emails())"

# Check email configuration in iris.md
grep -A 10 "email monitoring" /opt/ai-assistant/prompts/iris.md

# Check mailbox
mail

# Restart controller
sudo systemctl restart ai-wiggum
```

### Issue: Performance Degradation

**Symptoms:** New system slower than old system

**Diagnosis:**

```bash
# Check resource usage
ps aux | grep -E "wiggum|claude-code"

# Check disk I/O
iostat -x 1 10

# Check state file size
ls -lh /var/lib/ai-assistant/state.json

# Check database size
ls -lh ~/memory/iris.db
```

**Solutions:**

1. **State file too large:**
   - Review and prune self_notes
   - Reduce task queue snapshot size

2. **Too many voluntary exits:**
   - Increase exit threshold in iris.md
   - Check for exit trigger bugs

3. **Database slow:**
   - Run VACUUM: `sqlite3 ~/memory/iris.db "VACUUM;"`
   - Check for missing indexes

### Issue: Personality Changes

**Symptoms:** Iris behaving differently than before migration

**Solution:**

```bash
# Review personality section in state.json
cat /var/lib/ai-assistant/state.json | jq '.personality'

# Review self_notes
cat /var/lib/ai-assistant/state.json | jq '.self_notes'

# Manually update state.json to restore personality
nano /var/lib/ai-assistant/state.json

# Add learnings from backup:
cat ~/iris_migration_backup/YYYYMMDD/learnings.md

# Restart to load updated state
sudo systemctl restart ai-wiggum
```

### Issue: Unknown Sender Protocol Not Working

**Symptoms:** Unknown senders not getting dragon response

**Solution:**

```bash
# Check authorized sender list in iris.md
grep -A 5 "Authoritative contacts" /opt/ai-assistant/prompts/iris.md

# Should list:
# - owner-work@example.com
# - owner@example.com

# Test unknown sender detection
# Send test email from different address
# Attach and watch: tmux attach -t iris
```

### Issue: Need to Rollback

If migration has critical issues:

```bash
# Follow rollback procedure
cat ~/iris_migration_backup/$(date +%Y%m%d)/ROLLBACK.md

# Quick rollback:
1. Stop new system
   sudo systemctl stop ai-wiggum
   tmux kill-session -t iris

2. Restore database
   cp ~/iris_migration_backup/YYYYMMDD/iris.db.backup ~/memory/iris.db

3. Start old system
   [Your old startup method]

4. Notify Joshua
   mail -s "[Iris] Rolled back migration" owner-work@example.com
```

---

## Migration Success Criteria

Migration is successful when:

### Technical Criteria

- [ ] New system running continuously (no crashes)
- [ ] Email monitoring active and responsive
- [ ] Tasks being processed successfully
- [ ] State persisting across restarts
- [ ] Database updates working
- [ ] Worker spawning functional
- [ ] Voluntary exit/restart cycle working
- [ ] Resource usage within acceptable range
- [ ] All health checks passing

### Functional Criteria

- [ ] Email response time acceptable
- [ ] Task completion rate same or better
- [ ] No data loss
- [ ] No duplicate emails/tasks
- [ ] Personality continuity maintained
- [ ] All integrations working (Moltbook, Prolific, etc.)

### User Experience Criteria

- [ ] Joshua reports no issues
- [ ] Response quality unchanged or improved
- [ ] No confusion about migration
- [ ] Normal workflow restored

---

## Post-Migration Cleanup

After 30 days of successful operation:

### 1. Decommission Old System

```bash
# Remove old system files (if applicable)
# BE CAREFUL - verify new system stable first

# Archive old config
mkdir -p ~/iris_archive_old_system
mv [old iris files] ~/iris_archive_old_system/

# Document what was removed
echo "Old system archived on $(date)" > ~/iris_archive_old_system/README.txt
```

### 2. Consolidate Backups

```bash
# Keep migration backup for reference
tar czf ~/iris_migration_backup.tar.gz ~/iris_migration_backup/

# Move to safe storage
mv ~/iris_migration_backup.tar.gz ~/backups/
```

### 3. Update Documentation

```bash
# Mark migration as complete
echo "Migration completed successfully on $(date)" >> ~/iris/MIGRATION_LOG.md
echo "Old system: [description]" >> ~/iris/MIGRATION_LOG.md
echo "New system: Iris + Wiggum" >> ~/iris/MIGRATION_LOG.md
```

### 4. Establish New Baseline

```bash
# Document new system metrics
cat > ~/iris/BASELINE_METRICS.md << 'EOF'
# Baseline Metrics (Post-Migration)

Date established: [date]

## Performance
- Email response time: [measure]
- Task completion time: [measure]
- Voluntary exit frequency: [measure]

## Resource Usage
- Controller memory: [measure]
- Worker memory: [measure]
- Disk usage: [measure]

## Reliability
- Uptime: [measure]
- Crash frequency: [measure]
- Recovery time: [measure]
EOF
```

---

## Migration Checklist Summary

```
Pre-Migration:
[ ] Current state documented
[ ] Data backed up
[ ] Active tasks documented
[ ] New system tested
[ ] Rollback plan created

State Export:
[ ] State exported to new format
[ ] Learnings documented
[ ] Preferences transferred
[ ] Tasks migrated

Parallel Operation:
[ ] Both systems running
[ ] New system tested
[ ] Key workflows verified
[ ] 24-48 hour parallel run complete

Cutover:
[ ] Cutover window chosen
[ ] Joshua notified
[ ] Old system stopped
[ ] Final state synced
[ ] New system started
[ ] Test email sent
[ ] First hour monitored

Post-Migration:
[ ] 24-hour validation complete
[ ] First week testing complete
[ ] Metrics compared
[ ] Data integrity verified
[ ] User feedback received

Cleanup:
[ ] 30 days stable operation
[ ] Old system decommissioned
[ ] Backups consolidated
[ ] Documentation updated
[ ] New baseline established
```

---

**Migration Guide Complete**

**Version:** 1.0
**Last Updated:** February 16, 2026
**Status:** Ready for use
