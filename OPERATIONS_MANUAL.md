# Operations Manual: Iris + Wiggum

**Version:** 1.0
**Date:** February 16, 2026
**For:** Daily operation and maintenance of Iris + Wiggum AI assistant

This manual provides day-to-day operational procedures for monitoring, managing, and troubleshooting the Iris + Wiggum system.

---

## Table of Contents

1. [Starting and Stopping](#starting-and-stopping)
2. [Monitoring Health](#monitoring-health)
3. [Viewing Logs](#viewing-logs)
4. [Attaching to Tmux Sessions](#attaching-to-tmux-sessions)
5. [Managing the Task Queue](#managing-the-task-queue)
6. [Checking Resource Usage](#checking-resource-usage)
7. [Common Tasks and Procedures](#common-tasks-and-procedures)
8. [Troubleshooting](#troubleshooting)
9. [Maintenance Routines](#maintenance-routines)
10. [Emergency Procedures](#emergency-procedures)

---

## Starting and Stopping

### Check if Running

```bash
# Quick check - is service running?
systemctl is-active ai-wiggum

# Detailed status
systemctl status ai-wiggum

# Check for tmux session
tmux ls | grep iris
```

### Start the System

```bash
# Start wiggum service
sudo systemctl start ai-wiggum

# Verify started
systemctl status ai-wiggum

# Check tmux session appeared
sleep 5
tmux ls
```

**Expected result:**
- Service: `active (running)`
- Tmux session: `iris: 1 windows`

### Stop the System

**Graceful stop (recommended):**

```bash
# Attach to tmux and request graceful exit
tmux attach -t iris

# In tmux session, type:
Save state and exit gracefully now

# Wait for exit, then detach (Ctrl-B, D)
```

**Force stop:**

```bash
# Stop service (will try to stop gracefully)
sudo systemctl stop ai-wiggum

# If tmux session persists, kill it
tmux kill-session -t iris
```

### Restart the System

```bash
# Full restart (stops and starts service)
sudo systemctl restart ai-wiggum

# Verify
systemctl status ai-wiggum
tmux ls | grep iris
```

**When to restart:**
- After configuration changes
- After updating prompt files
- When controller appears stuck
- For routine maintenance

### Enable/Disable Auto-Start

```bash
# Enable (start on boot)
sudo systemctl enable ai-wiggum

# Disable (don't start on boot)
sudo systemctl disable ai-wiggum

# Check current setting
systemctl is-enabled ai-wiggum
```

---

## Monitoring Health

### Quick Health Check

```bash
# Check if iris tmux session is running
tmux has-session -t iris && echo "✓ Iris running" || echo "✗ Iris not running"

# Check state file
cat /home/claude/iris/state.json | python3 -m json.tool > /dev/null && \
  echo "✓ State valid" || echo "✗ State corrupted"

# Check database
sqlite3 /home/claude/iris/scripts/state/iris.db "PRAGMA integrity_check;"
```

**Expected output:**
```
=== Iris + Wiggum Health Check ===
Date: [timestamp]

Service Status:
✓ Service running

Controller Status:
✓ Controller running

State File:
✓ State file exists
✓ State file valid JSON

Database:
✓ Database exists

Resource Usage:
  wiggum.sh: 5 MB
  claude-code: 350 MB

=== Health Check Complete ===
```

### Detailed Health Check

```bash
# Service health
systemctl status ai-wiggum

# Controller health
tmux has-session -t iris && echo "✓ Running" || echo "✗ Not running"

# State file health
cat /home/claude/iris/state.json | python3 -m json.tool > /dev/null && \
  echo "✓ State valid" || echo "✗ State corrupted"

# State file freshness
stat /home/claude/iris/state.json | grep Modify

# Database health
sqlite3 /home/claude/iris/scripts/state/iris.db "PRAGMA integrity_check;"

# Database size
du -sh /home/claude/iris/scripts/state/iris.db

# Disk space
df -h /var/lib/ai-assistant
df -h /home/claude

# Memory usage
free -h
ps aux | grep -E "wiggum|claude-code" | grep -v grep
```

### Continuous Monitoring

```bash
# Watch service status
watch -n 5 'systemctl is-active ai-wiggum && tmux has-session -t iris'

# Watch resource usage
watch -n 10 'ps aux | grep -E "wiggum|claude-code" | grep -v grep'

# Watch state file updates
watch -n 30 'stat /home/claude/iris/state.json | grep Modify'

# Monitor all in one terminal (using tmux)
tmux new-session -s monitor \; \
  split-window -h \; \
  split-window -v \; \
  select-pane -t 0 \; \
  send-keys 'journalctl -u ai-wiggum -f' C-m \; \
  select-pane -t 1 \; \
  send-keys 'watch -n 5 systemctl status ai-wiggum' C-m \; \
  select-pane -t 2 \; \
  send-keys 'htop' C-m
```

---

## Viewing Logs

### Systemd Journal Logs

```bash
# View recent logs
journalctl -u ai-wiggum -n 50

# Follow logs (live tail)
journalctl -u ai-wiggum -f

# Logs since last boot
journalctl -u ai-wiggum -b

# Logs from last hour
journalctl -u ai-wiggum --since "1 hour ago"

# Logs from specific date
journalctl -u ai-wiggum --since "2026-02-15" --until "2026-02-16"

# Search logs
journalctl -u ai-wiggum | grep -i error
journalctl -u ai-wiggum | grep -i crash

# Export logs
journalctl -u ai-wiggum --since today > ~/iris_logs_$(date +%Y%m%d).txt
```

### Master Log

```bash
# View recent activity
tail -n 50 ~/master_log.md

# Follow master log
tail -f ~/master_log.md

# Search master log
grep -i "error" ~/master_log.md
grep -i "task complete" ~/master_log.md

# View today's activity
grep "$(date +%Y-%m-%d)" ~/master_log.md
```

### State File (Current Status)

```bash
# View entire state
cat /home/claude/iris/state.json | jq .

# View specific sections
cat /home/claude/iris/state.json | jq '.personality'
cat /home/claude/iris/state.json | jq '.active_tasks'
cat /home/claude/iris/state.json | jq '.recent_context'
cat /home/claude/iris/state.json | jq '.statistics'
cat /home/claude/iris/state.json | jq '.self_notes'

# Watch state updates
watch -n 10 'cat /home/claude/iris/state.json | jq .statistics'
```

### Database Activity

```bash
# Recent emails
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT datetime(timestamp, 'unixepoch') as time, sender, subject
FROM emails
ORDER BY timestamp DESC
LIMIT 10;
EOF

# Recent tasks
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT datetime(created_at, 'unixepoch') as created, title, status, priority
FROM tasks
ORDER BY created_at DESC
LIMIT 10;
EOF

# Activity log
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT datetime(timestamp, 'unixepoch') as time, event_type, description
FROM activity_log
ORDER BY timestamp DESC
LIMIT 20;
EOF

# Statistics
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT 'Total emails:', COUNT(*) FROM emails;
SELECT 'Unread emails:', COUNT(*) FROM emails WHERE read = 0;
SELECT 'Total tasks:', COUNT(*) FROM tasks;
SELECT 'Active tasks:', COUNT(*) FROM tasks WHERE status IN ('pending', 'in_progress');
SELECT 'Completed today:', COUNT(*) FROM tasks WHERE status = 'completed' AND DATE(created_at, 'unixepoch') = DATE('now');
EOF
```

---

## Attaching to Tmux Sessions

### Basic Attachment

```bash
# Attach to watch Iris work
tmux attach -t iris

# Detach without killing session
# Press: Ctrl-B, then D
```

### Read-Only Attachment

```bash
# Attach in read-only mode (can't accidentally type)
tmux attach -t iris -r
```

### What You'll See

When attached, you'll see:
- Controller initialization (on startup)
- Email checking loop
- Task processing
- Worker spawning
- State updates
- Voluntary exit decisions
- Any errors or issues

### Interacting with Controller

While attached, you can type commands to Iris:

**Check status:**
```
Report current status including task queue and recent activity
```

**Force email check:**
```
Check for new email immediately
```

**Request voluntary exit:**
```
Save state and exit gracefully for context refresh
```

**View state:**
```
Display current state.json contents
```

**Manual task:**
```
[Any task instruction you want Iris to do]
```

### Tmux Shortcuts

```bash
# Detach
Ctrl-B, D

# Scroll mode (read history)
Ctrl-B, [
# Then use arrow keys, Page Up/Down
# Press Q to exit scroll mode

# Clear screen
Ctrl-L

# Search (in scroll mode)
Ctrl-B, [
Then: Ctrl-S (forward) or Ctrl-R (backward)
Type search term, Enter
```

---

## Managing the Task Queue

### View Task Queue

```bash
# From state.json
cat /home/claude/iris/state.json | jq '.task_queue'

# From database
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT
  id,
  title,
  status,
  priority,
  datetime(created_at, 'unixepoch') as created
FROM tasks
WHERE status IN ('pending', 'in_progress')
ORDER BY priority DESC, created_at ASC;
EOF
```

### View Active Tasks

```bash
# From state.json (current work)
cat /home/claude/iris/state.json | jq '.active_tasks'

# From database (all in-progress)
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT
  title,
  description,
  status,
  datetime(created_at, 'unixepoch') as created
FROM tasks
WHERE status = 'in_progress';
EOF
```

### Add Task Manually

**Via email (recommended):**
```bash
mail -s "Task: [description]" claude@mail.example.com << 'EOF'
[Task details]
EOF
```

**Via tmux (direct):**
```bash
tmux attach -t iris

# Type in session:
New task: [description]
Priority: [high/medium/low]
[Details]

# Detach: Ctrl-B, D
```

**Via database (advanced):**
```bash
sqlite3 /home/claude/iris/scripts/state/iris.db << EOF
INSERT INTO tasks (title, description, status, priority, created_at)
VALUES (
  'Task title',
  'Task description',
  'pending',
  2,
  $(date +%s)
);
EOF
```

### Update Task Status

**Via tmux:**
```bash
tmux attach -t iris

# Type:
Mark task [task_id] as completed with results: [results]
```

**Via database:**
```bash
sqlite3 /home/claude/iris/scripts/state/iris.db << EOF
UPDATE tasks
SET status = 'completed',
    completed_at = $(date +%s)
WHERE id = [task_id];
EOF
```

### Cancel Task

**Via tmux:**
```bash
tmux attach -t iris

# Type:
Cancel task [task_id] with reason: [reason]
```

**Via database:**
```bash
sqlite3 /home/claude/iris/scripts/state/iris.db << EOF
UPDATE tasks
SET status = 'cancelled'
WHERE id = [task_id];
EOF
```

---

## Checking Resource Usage

### CPU and Memory

```bash
# Overall system
htop

# Specific to Iris
ps aux | grep -E "wiggum|claude-code" | grep -v grep

# Detailed per process
top -p $(pgrep -d',' -f "wiggum|claude-code")

# Memory breakdown
ps aux | grep -E "wiggum|claude-code" | awk '{print $11, $6/1024, "MB"}'
```

### Disk Usage

```bash
# Overall
df -h

# Iris-specific directories
du -sh /opt/ai-assistant
du -sh /var/lib/ai-assistant
du -sh /var/log/ai-assistant
du -sh /home/claude/iris/scripts/state/iris.db
du -sh ~/docs/emails

# State file size
ls -lh /home/claude/iris/state.json

# Find large files
find /var/lib/ai-assistant -type f -size +10M -ls
```

### Network Usage

```bash
# Monitor network connections
ss -tunap | grep -E "wiggum|claude-code|iris"

# Email-related connections
ss -tunap | grep -E "25|587|993"  # SMTP, IMAP ports
```

### Resource Limits

```bash
# Check systemd limits
systemctl show ai-wiggum | grep -i memory

# Check current usage against limits
ps aux | grep -E "wiggum|claude-code" | \
  awk '{sum+=$6} END {print "Total:", sum/1024, "MB / 256 MB limit"}'
```

---

## Common Tasks and Procedures

### Force Voluntary Exit (Context Refresh)

```bash
# Method 1: Via tmux
tmux attach -t iris
# Type: Save state and exit gracefully now
# Detach: Ctrl-B, D

# Method 2: Kill session (wiggum will respawn)
tmux kill-session -t iris

# Verify respawn
sleep 5
tmux ls | grep iris
```

### Send Email as Iris

```bash
# Use email tools
cd /home/claude/iris/scripts/mail
python3 << 'EOF'
from server import send_email

send_email(
    to="owner-work@example.com",
    subject="[Subject]",
    body="[Body]"
)
EOF
```

### Check for New Email Manually

```bash
cd /home/claude/iris/scripts/mail
python3 -c "from server import check_new_emails; print(check_new_emails())"
```

### Backup State and Database

```bash
# Create backup directory
mkdir -p ~/iris_backups/$(date +%Y%m%d)

# Backup state file
cp /home/claude/iris/state.json \
   ~/iris_backups/$(date +%Y%m%d)/state.json

# Backup database
cp /home/claude/iris/scripts/state/iris.db \
   ~/iris_backups/$(date +%Y%m%d)/iris.db

# Backup master log
cp ~/master_log.md \
   ~/iris_backups/$(date +%Y%m%d)/master_log.md

# Create archive
tar czf ~/iris_backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  ~/iris_backups/$(date +%Y%m%d)

# Verify backup
ls -lh ~/iris_backups/backup_*.tar.gz | tail -1
```

### Restore from Backup

```bash
# Stop system first
sudo systemctl stop ai-wiggum
tmux kill-session -t iris 2>/dev/null

# Restore state file
cp ~/iris_backups/YYYYMMDD/state.json \
   /home/claude/iris/state.json

# Restore database
cp ~/iris_backups/YYYYMMDD/iris.db \
   /home/claude/iris/scripts/state/iris.db

# Restart system
sudo systemctl start ai-wiggum
```

### Update Controller Prompt

```bash
# Edit prompt file
sudo nano /home/claude/iris/prompts/iris.md

# Changes take effect on next controller start
# Force restart to apply immediately
sudo systemctl restart ai-wiggum
```

### Update Worker Template

```bash
# Edit worker template
sudo nano /home/claude/iris/prompts/workers/[worker_name].md

# Changes take effect when worker is next spawned
# No restart needed
```

### Clear Task Queue

**Warning:** This deletes pending tasks!

```bash
# View pending tasks first
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT id, title, status FROM tasks WHERE status = 'pending';
EOF

# Confirm, then clear
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
UPDATE tasks SET status = 'cancelled' WHERE status = 'pending';
EOF

# Update state.json
cat /home/claude/iris/state.json | \
  jq '.task_queue.queue_snapshot = [] | .task_queue.total_pending = 0' | \
  sponge /home/claude/iris/state.json
# Note: Install sponge with: sudo apt-get install moreutils
# Or use temp file method:
# cat ... > /tmp/state.json && mv /tmp/state.json /home/claude/iris/state.json
```

### Vacuum Database

```bash
# Reclaim space and optimize
sqlite3 /home/claude/iris/scripts/state/iris.db "VACUUM;"

# Check size before/after
du -h /home/claude/iris/scripts/state/iris.db
```

### Rotate Logs

```bash
# Archive old journal logs
sudo journalctl --rotate
sudo journalctl --vacuum-time=30d

# Archive master log
mv ~/master_log.md ~/master_log_$(date +%Y%m%d).md
touch ~/master_log.md
```

---

## Troubleshooting

### Controller Not Running

**Check:**
```bash
systemctl status ai-wiggum
journalctl -u ai-wiggum -n 50
tmux ls
```

**Solutions:**

1. **Service not running:**
   ```bash
   sudo systemctl start ai-wiggum
   ```

2. **Tmux session missing:**
   ```bash
   # Service should spawn it, wait 10 seconds
   sleep 10
   tmux ls
   ```

3. **Controller crashing:**
   ```bash
   # Attach to see crash
   tmux attach -t iris
   # Watch for error message

   # Check state file
   cat /home/claude/iris/state.json | jq .
   # If invalid, restore from backup
   ```

### Email Not Being Processed

**Check:**
```bash
# Test email tools
cd /home/claude/iris/scripts/mail
python3 -c "from server import check_new_emails; print(check_new_emails())"

# Check mailbox
mail

# Attach and watch controller
tmux attach -t iris
```

**Solutions:**

1. **Email tools not working:**
   ```bash
   # Check mail server
   systemctl status postfix

   # Check mailbox permissions
   ls -l /var/mail/claude
   ```

2. **Controller not checking email:**
   ```bash
   # Force email check via tmux
   tmux attach -t iris
   # Type: Check for new email immediately
   ```

### High Memory Usage

**Check:**
```bash
ps aux | grep -E "wiggum|claude-code" | awk '{print $11, $6/1024, "MB"}'
```

**Solutions:**

1. **Controller using too much:**
   ```bash
   # Force voluntary exit
   tmux kill-session -t iris
   # Wiggum will respawn fresh
   ```

2. **Multiple workers:**
   ```bash
   # Check for stuck workers
   ps aux | grep claude-code

   # Kill stuck workers
   pkill -f "claude-code.*worker"
   ```

3. **Reduce voluntary exit threshold:**
   ```bash
   # Edit iris.md to exit more frequently
   sudo nano /home/claude/iris/prompts/iris.md
   # Adjust token threshold or task count
   ```

### State File Corrupted

**Check:**
```bash
cat /home/claude/iris/state.json | jq .
```

**Solution:**
```bash
# Stop controller
sudo systemctl stop ai-wiggum

# Backup corrupted file
cp /home/claude/iris/state.json \
   /home/claude/iris/state.json.corrupted.$(date +%s)

# Restore from backup
cp ~/iris_backups/LATEST/state.json \
   /home/claude/iris/state.json

# Or create fresh state
cat > /home/claude/iris/state.json << 'EOF'
{
  "last_session_end": null,
  "exit_reason": "state_recovery",
  "personality": {
    "name": "Iris",
    "identity": "AI assistant for Joshua",
    "awareness": "Recovered from state file corruption",
    "recent_tone": "Professional, helpful"
  },
  "active_tasks": [],
  "recent_context": {},
  "task_queue": {"total_pending": 0, "queue_snapshot": []},
  "self_notes": [],
  "statistics": {}
}
EOF

# Restart
sudo systemctl start ai-wiggum
```

### Database Issues

**Check integrity:**
```bash
sqlite3 /home/claude/iris/scripts/state/iris.db "PRAGMA integrity_check;"
```

**Repair:**
```bash
# Backup first
cp /home/claude/iris/scripts/state/iris.db /home/claude/iris/scripts/state/iris.db.backup.$(date +%s)

# Attempt repair
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
PRAGMA integrity_check;
REINDEX;
VACUUM;
EOF
```

**Restore from backup:**
```bash
cp ~/iris_backups/LATEST/iris.db /home/claude/iris/scripts/state/iris.db
```

### Disk Full

**Check:**
```bash
df -h
```

**Clean up:**
```bash
# Clear journal logs
sudo journalctl --vacuum-size=100M

# Clear old task outputs
find /var/lib/ai-assistant/tasks -type f -mtime +30 -delete

# Vacuum database
sqlite3 /home/claude/iris/scripts/state/iris.db "VACUUM;"

# Clear old email files (be careful!)
# Review first: ls -lt ~/docs/emails/
```

---

## Maintenance Routines

### Daily

```bash
#!/bin/bash
# Daily maintenance script

echo "=== Daily Maintenance $(date) ==="

# Health check
tmux has-session -t iris && echo "✓ Iris running" || echo "✗ Iris not running"

# Check for errors
echo "Checking for errors in last 24 hours..."
journalctl -u ai-wiggum --since "24 hours ago" | grep -i error | wc -l

# Check disk usage
echo "Disk usage:"
df -h / | tail -1

# Check database size
echo "Database size:"
du -sh /home/claude/iris/scripts/state/iris.db

# Check state file freshness
echo "State file last modified:"
stat /home/claude/iris/state.json | grep Modify

echo "=== Daily Maintenance Complete ==="
```

### Weekly

```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly Maintenance $(date) ==="

# Backup state and database
mkdir -p ~/iris_backups/weekly/$(date +%Y%m%d)
cp /home/claude/iris/state.json ~/iris_backups/weekly/$(date +%Y%m%d)/
cp /home/claude/iris/scripts/state/iris.db ~/iris_backups/weekly/$(date +%Y%m%d)/
cp ~/master_log.md ~/iris_backups/weekly/$(date +%Y%m%d)/

# Vacuum database
echo "Vacuuming database..."
sqlite3 /home/claude/iris/scripts/state/iris.db "VACUUM;"

# Check database integrity
echo "Checking database integrity..."
sqlite3 /home/claude/iris/scripts/state/iris.db "PRAGMA integrity_check;"

# Review self-notes
echo "Current self-notes:"
cat /home/claude/iris/state.json | jq '.self_notes'

# Review statistics
echo "Week statistics:"
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT
  DATE(created_at, 'unixepoch') as date,
  COUNT(*) as tasks
FROM tasks
WHERE created_at > unixepoch('now', '-7 days')
GROUP BY date
ORDER BY date;
EOF

# Clean old task directories
find /var/lib/ai-assistant/tasks -type d -mtime +30 -exec rm -rf {} \; 2>/dev/null

echo "=== Weekly Maintenance Complete ==="
```

### Monthly

```bash
#!/bin/bash
# Monthly maintenance script

echo "=== Monthly Maintenance $(date) ==="

# Full backup
tar czf ~/iris_backups/monthly_$(date +%Y%m).tar.gz \
  /opt/ai-assistant \
  /var/lib/ai-assistant \
  /home/claude/iris/scripts/state/iris.db \
  ~/master_log.md

# Rotate logs
sudo journalctl --rotate
sudo journalctl --vacuum-time=90d

# Archive master log
mv ~/master_log.md ~/master_log_$(date +%Y%m).md
touch ~/master_log.md
echo "# Master Log" > ~/master_log.md
echo "" >> ~/master_log.md
echo "Started: $(date)" >> ~/master_log.md

# Review and prune self-notes
echo "Review self-notes for outdated entries"
cat /home/claude/iris/state.json | jq '.self_notes'

# Performance review
echo "Monthly statistics:"
sqlite3 /home/claude/iris/scripts/state/iris.db << 'EOF'
SELECT 'Total emails:', COUNT(*) FROM emails WHERE timestamp > unixepoch('now', '-30 days');
SELECT 'Total tasks:', COUNT(*) FROM tasks WHERE created_at > unixepoch('now', '-30 days');
SELECT 'Completed tasks:', COUNT(*) FROM tasks WHERE status = 'completed' AND created_at > unixepoch('now', '-30 days');
EOF

# Restart for fresh start
echo "Restarting for monthly refresh..."
sudo systemctl restart ai-wiggum

echo "=== Monthly Maintenance Complete ==="
```

---

## Emergency Procedures

### Complete System Failure

```bash
# 1. Stop everything
sudo systemctl stop ai-wiggum
tmux kill-session -t iris 2>/dev/null
pkill -f claude-code

# 2. Check what failed
journalctl -u ai-wiggum -n 100
dmesg | tail -50
df -h
free -h

# 3. Restore from backup
cp ~/iris_backups/LATEST/state.json /home/claude/iris/state.json
cp ~/iris_backups/LATEST/iris.db /home/claude/iris/scripts/state/iris.db

# 4. Restart
sudo systemctl start ai-wiggum

# 5. Verify
systemctl status ai-wiggum
tmux ls
```

### Database Corruption

```bash
# 1. Stop system
sudo systemctl stop ai-wiggum

# 2. Backup corrupted database
cp /home/claude/iris/scripts/state/iris.db /home/claude/iris/scripts/state/iris.db.corrupted.$(date +%s)

# 3. Attempt recovery
sqlite3 /home/claude/iris/scripts/state/iris.db ".recover" | sqlite3 ~/memory/iris_recovered.db

# 4. Verify recovered database
sqlite3 ~/memory/iris_recovered.db "PRAGMA integrity_check;"

# 5. If OK, replace
mv /home/claude/iris/scripts/state/iris.db /home/claude/iris/scripts/state/iris.db.old
mv ~/memory/iris_recovered.db /home/claude/iris/scripts/state/iris.db

# 6. Restart
sudo systemctl start ai-wiggum
```

### Infinite Crash Loop

```bash
# 1. Stop wiggum to prevent respawn
sudo systemctl stop ai-wiggum

# 2. Identify crash cause
journalctl -u ai-wiggum -n 200 | grep -i error

# 3. Test controller manually
cd /opt/ai-assistant
tmux new -s iris-test "claude-code --prompt-file prompts/iris.md"

# 4. Watch for crash, debug

# 5. Fix issue (state file, prompt, permissions, etc.)

# 6. Restart service
sudo systemctl start ai-wiggum
```

### Email Storm (Too Many Emails)

```bash
# 1. Temporarily stop email processing
tmux attach -t iris
# Type: Pause email monitoring until further notice

# 2. Check email volume
mail
# Count unread emails

# 3. Manually review and delete spam/unwanted

# 4. Resume email processing
tmux attach -t iris
# Type: Resume email monitoring
```

### Disk Full

```bash
# 1. Check what's full
df -h
du -sh /* | sort -h | tail -20

# 2. Emergency cleanup
sudo journalctl --vacuum-size=50M
find /tmp -type f -mtime +7 -delete
sqlite3 /home/claude/iris/scripts/state/iris.db "VACUUM;"

# 3. Clear old task outputs
find /var/lib/ai-assistant/tasks -type f -mtime +7 -delete

# 4. Verify space available
df -h

# 5. Restart if needed
sudo systemctl restart ai-wiggum
```

---

## Quick Reference

### Essential Commands

```bash
# Status
systemctl status ai-wiggum
tmux ls | grep iris

# Attach
tmux attach -t iris

# Logs
journalctl -u ai-wiggum -f

# Restart
sudo systemctl restart ai-wiggum

# Health check
tmux has-session -t iris && echo "✓ Iris running" || echo "✗ Iris not running"

# State
cat /home/claude/iris/state.json | jq .
```

### Important Files

```
/home/claude/iris/wiggum.sh              - Respawn loop
/home/claude/iris/prompts/iris.md        - Controller prompt
/home/claude/iris/state.json             - Current state
/home/claude/iris/iris.db               - Database (symlinked from scripts/state/)
/home/claude/iris/scripts/state/iris.db - Actual database file
/home/claude/iris/controller.log        - Controller log
/etc/systemd/system/ai-wiggum.service   - Service definition
```

**NOTE:** The old paths `/home/claude/iris/` and `/var/lib/ai-assistant/` are from
an earlier deployment design and are NOT used. Everything is under `/home/claude/iris/`.

### Support Contacts

- **Owner:** Joshua (owner@example.com)
- **Documentation:** /home/claude/iris/README.md
- **Architecture:** /home/claude/iris/revised-architecture.md
- **Deployment:** /home/claude/iris/DEPLOYMENT_GUIDE.md

---

**Operations Manual Complete**

**Version:** 1.0
**Last Updated:** February 16, 2026
**Status:** Production-ready
