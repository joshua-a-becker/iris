# Deployment Guide: Iris + Wiggum

**Version:** 1.0
**Date:** February 16, 2026
**Target Environment:** Production Linux server (Digital Ocean, 2-core/4GB RAM)

This guide provides step-by-step instructions for deploying the Iris + Wiggum AI assistant from development to production.

---

## Table of Contents

1. [Pre-Deployment Validation](#pre-deployment-validation)
2. [File Path Migration](#file-path-migration)
3. [Systemd Service Installation](#systemd-service-installation)
4. [Database Setup](#database-setup)
5. [Email Configuration](#email-configuration)
6. [First Run Procedure](#first-run-procedure)
7. [Monitoring and Health Checks](#monitoring-and-health-checks)
8. [Rollback Procedure](#rollback-procedure)
9. [Post-Deployment Checklist](#post-deployment-checklist)

---

## Pre-Deployment Validation

### 1. Run Complete Test Suite

```bash
cd ~/iris/tests
./run_all_tests.sh
```

**Expected result:** All tests pass (100% pass rate)

If any tests fail, **stop** and investigate before proceeding.

### 2. Verify File Structure

```bash
cd ~/iris
ls -la

# Should see:
# - wiggum.sh (executable)
# - prompts/iris.md
# - prompts/workers/ (5 templates)
# - scripts/mail/ (server.py, read_mbox.py)
# - scripts/state/ (state_manager.py, db.py)
# - config/ai-wiggum.service
# - tests/ (8 test files)
```

### 3. Complete Validation Checklist

```bash
cat ~/iris/tests/VALIDATION_CHECKLIST.md
```

Work through all 148 validation items. Mark each item as complete.

**Critical items:**

- [ ] All test suites pass
- [ ] Database accessible
- [ ] Email tools functional
- [ ] State manager works
- [ ] Wiggum loop tested manually
- [ ] Worker templates validated
- [ ] File permissions correct

### 4. Check Dependencies

```bash
# Python 3
python3 --version  # Should be 3.8+

# Required Python packages
python3 -c "import json, sqlite3, pathlib, datetime" && echo "Core packages OK"

# Tmux
tmux -V  # Should be 2.0+

# Systemd
systemctl --version  # Should be present

# Mail tools
cd ~/iris/scripts/mail && python3 -c "from server import check_new_emails" && echo "Email tools OK"

# Database helper
cd ~/iris/scripts/state && python3 -c "from db import get_connection" && echo "Database helper OK"

# State manager
cd ~/iris/scripts/state && python3 -c "from state_manager import load_state, save_state" && echo "State manager OK"
```

### 5. Backup Current System

```bash
# Backup current state (if migrating from existing Iris)
cp ~/iris/state.json ~/iris/state.json.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No existing state"

# Backup database
cp ~/memory/iris.db ~/memory/iris.db.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No existing database"

# Backup master log
cp ~/master_log.md ~/master_log.md.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo "No existing log"
```

---

## File Path Migration

The system is developed at `~/iris/` but deployed to `/opt/ai-assistant/`.

### 1. Create Production Directories

```bash
# Create base directory (requires sudo)
sudo mkdir -p /opt/ai-assistant
sudo mkdir -p /opt/ai-assistant/prompts/workers
sudo mkdir -p /opt/ai-assistant/scripts/mail
sudo mkdir -p /opt/ai-assistant/scripts/state
sudo mkdir -p /opt/ai-assistant/scripts/health
sudo mkdir -p /var/lib/ai-assistant
sudo mkdir -p /var/lib/ai-assistant/tasks
sudo mkdir -p /var/log/ai-assistant

# Set ownership
sudo chown -R claude:claude /opt/ai-assistant
sudo chown -R claude:claude /var/lib/ai-assistant
sudo chown -R claude:claude /var/log/ai-assistant
```

### 2. Copy Files to Production

```bash
# Core files
sudo cp ~/iris/wiggum.sh /opt/ai-assistant/
sudo cp ~/iris/prompts/iris.md /opt/ai-assistant/prompts/
sudo cp ~/iris/prompts/workers/*.md /opt/ai-assistant/prompts/workers/

# Scripts
sudo cp ~/iris/scripts/mail/*.py /opt/ai-assistant/scripts/mail/
sudo cp ~/iris/scripts/state/*.py /opt/ai-assistant/scripts/state/

# Documentation (optional, for reference)
sudo cp ~/iris/README.md /opt/ai-assistant/
sudo cp ~/iris/revised-architecture.md /opt/ai-assistant/
sudo cp ~/iris/OPERATIONS_MANUAL.md /opt/ai-assistant/

# Set ownership
sudo chown -R claude:claude /opt/ai-assistant
```

### 3. Make Scripts Executable

```bash
sudo chmod +x /opt/ai-assistant/wiggum.sh
sudo chmod +x /opt/ai-assistant/scripts/mail/*.py
sudo chmod +x /opt/ai-assistant/scripts/state/*.py
```

### 4. Update File Paths in Configuration

**Edit systemd service file:**

```bash
# Copy service file
sudo cp ~/iris/config/ai-wiggum.service /etc/systemd/system/

# Edit service file
sudo nano /etc/systemd/system/ai-wiggum.service
```

Update `ExecStart` path:

```ini
# Change from:
ExecStart=/home/claude/iris/wiggum.sh

# To:
ExecStart=/opt/ai-assistant/wiggum.sh
```

**Edit wiggum.sh:**

```bash
sudo nano /opt/ai-assistant/wiggum.sh
```

Update prompt file path:

```bash
# Change from:
claude-code --prompt-file /home/claude/iris/prompts/iris.md

# To:
claude-code --prompt-file /opt/ai-assistant/prompts/iris.md
```

**Edit iris.md (controller prompt):**

```bash
sudo nano /opt/ai-assistant/prompts/iris.md
```

Update references to:

```markdown
# Change:
~/iris/scripts/state/state_manager.py
~/iris/scripts/state/db.py
~/iris/scripts/mail/server.py

# To:
/opt/ai-assistant/scripts/state/state_manager.py
/opt/ai-assistant/scripts/state/db.py
/opt/ai-assistant/scripts/mail/server.py

# Change state file location:
~/iris/state.json
# To:
/var/lib/ai-assistant/state.json
```

### 5. Path Summary

| Resource | Development | Production |
|----------|-------------|------------|
| Base directory | ~/iris/ | /opt/ai-assistant/ |
| Wiggum script | ~/iris/wiggum.sh | /opt/ai-assistant/wiggum.sh |
| Controller prompt | ~/iris/prompts/iris.md | /opt/ai-assistant/prompts/iris.md |
| Worker templates | ~/iris/prompts/workers/ | /opt/ai-assistant/prompts/workers/ |
| State file | ~/iris/state.json | /var/lib/ai-assistant/state.json |
| Task storage | ~/iris/tasks/ | /var/lib/ai-assistant/tasks/ |
| Database | ~/memory/iris.db | ~/memory/iris.db (unchanged) |
| Master log | ~/master_log.md | ~/master_log.md (unchanged) |
| Email storage | ~/docs/emails/ | ~/docs/emails/ (unchanged) |
| Logs | journalctl | /var/log/ai-assistant/ + journalctl |

**Note:** Database, master log, and email storage remain in home directory for continuity.

---

## Systemd Service Installation

### 1. Reload Systemd

```bash
sudo systemctl daemon-reload
```

### 2. Enable Service (Start on Boot)

```bash
sudo systemctl enable ai-wiggum
```

**Expected output:**
```
Created symlink /etc/systemd/system/multi-user.target.wants/ai-wiggum.service → /etc/systemd/system/ai-wiggum.service.
```

### 3. Verify Service Configuration

```bash
systemctl cat ai-wiggum
```

Check that:
- ExecStart points to `/opt/ai-assistant/wiggum.sh`
- User is `claude`
- WorkingDirectory is `/home/claude`
- Restart is `always`

### 4. Test Service (Dry Run)

Before starting for real, test the service:

```bash
# Start service
sudo systemctl start ai-wiggum

# Check status immediately
systemctl status ai-wiggum

# Watch logs
journalctl -u ai-wiggum -f
```

**Expected behavior:**
- Service should start successfully
- Wiggum loop should spawn tmux session
- Controller should start (you'll see Claude Code output in logs)

**If successful, stop for now:**

```bash
sudo systemctl stop ai-wiggum
tmux kill-session -t iris 2>/dev/null
```

---

## Database Setup

The database remains at `~/memory/iris.db` for continuity.

### 1. Verify Database Exists

```bash
ls -lh ~/memory/iris.db
```

If database doesn't exist, it will be created on first run.

### 2. Test Database Connection

```bash
cd /opt/ai-assistant/scripts/state
python3 << 'EOF'
from db import get_connection, init_database

# Test connection
conn = get_connection()
print("✓ Database connection successful")

# Initialize tables if needed
init_database()
print("✓ Database initialized")

# Test basic query
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM tasks")
count = cursor.fetchone()[0]
print(f"✓ Found {count} tasks in database")

conn.close()
EOF
```

### 3. Initialize Database Schema

```bash
cd /opt/ai-assistant/scripts/state
python3 -c "from db import init_database; init_database(); print('✓ Database schema ready')"
```

### 4. Verify Tables

```bash
sqlite3 ~/memory/iris.db "SELECT name FROM sqlite_master WHERE type='table';"
```

**Expected tables:**
- emails
- tasks
- activity_log
- state_kv

---

## Email Configuration

### 1. Verify Email Tools

```bash
cd /opt/ai-assistant/scripts/mail
python3 << 'EOF'
from server import check_new_emails, list_emails

# Test mailbox access
print("Testing email tools...")
result = check_new_emails()
print(f"✓ Email tools working: {result}")

# List recent emails
emails = list_emails(limit=5)
print(f"✓ Found {len(emails)} recent emails")
EOF
```

### 2. Test Email Sending

```bash
cd /opt/ai-assistant/scripts/mail
python3 << 'EOF'
from server import send_email

# Send test email to Joshua
result = send_email(
    to="owner-work@example.com",
    subject="[Iris] Deployment Test",
    body="""This is a test email from Iris + Wiggum deployment.

If you receive this, email sending is working correctly.

-- Iris (automated test)
"""
)

print(f"✓ Test email sent: {result}")
EOF
```

### 3. Configure Authorized Senders

Verify authorized senders are configured in `/opt/ai-assistant/prompts/iris.md`:

```bash
grep -A 5 "Authoritative contacts" /opt/ai-assistant/prompts/iris.md
```

**Should show:**
- owner-work@example.com
- owner@example.com

### 4. Test Email Monitoring

```bash
# Test email check loop (30 seconds)
timeout 30 bash -c 'while true; do \
  cd /opt/ai-assistant/scripts/mail && \
  python3 -c "from server import check_new_emails; print(check_new_emails())" && \
  sleep 5; \
done'
```

---

## First Run Procedure

### 1. Initialize State File

Create initial state.json if it doesn't exist:

```bash
cat > /var/lib/ai-assistant/state.json << 'EOF'
{
  "last_session_end": null,
  "exit_reason": "initial_deployment",
  "personality": {
    "name": "Iris",
    "identity": "AI assistant for Joshua",
    "awareness": "First deployment of Iris + Wiggum architecture",
    "recent_tone": "Professional, helpful",
    "relationship_notes": "Just deployed, ready to start working"
  },
  "active_tasks": [],
  "recent_context": {
    "last_email": null,
    "last_action": "Initial deployment",
    "waiting_for": "First email or task"
  },
  "task_queue": {
    "total_pending": 0,
    "highest_priority": null,
    "queue_snapshot": []
  },
  "self_notes": [
    "Just deployed, ready to start working",
    "Email response protocol: ack immediately, update on completion",
    "Unknown senders get dragon-themed response + forward to Joshua"
  ],
  "statistics": {
    "total_sessions": 0,
    "tasks_completed_today": 0,
    "context_refreshes_today": 0,
    "last_error": null
  }
}
EOF

# Set ownership
sudo chown claude:claude /var/lib/ai-assistant/state.json
```

### 2. Start the Service

```bash
sudo systemctl start ai-wiggum
```

### 3. Verify Service Started

```bash
# Check service status
systemctl status ai-wiggum

# Should show:
# Active: active (running)
```

### 4. Verify Tmux Session

```bash
# Check for iris tmux session
tmux ls

# Should show:
# iris: 1 windows (created ...)
```

### 5. Attach to Watch First Startup

```bash
tmux attach -t iris
```

**What to watch for:**

1. Controller loads state.json
2. Controller initializes
3. Controller starts email monitoring loop
4. Controller logs "Session started" or similar

**Detach:** Press `Ctrl-B`, then `D`

### 6. Monitor Logs

```bash
# Watch logs in real-time
journalctl -u ai-wiggum -f
```

### 7. Send Test Email

From another terminal or email client:

```bash
mail -s "Test: First Iris task" claude@mail.example.com << 'EOF'
Hello Iris,

This is a test email to verify you're receiving and processing emails.

Please acknowledge this message.

Joshua
EOF
```

**Expected behavior:**

1. Iris detects email within 5-10 seconds
2. Iris sends immediate acknowledgment
3. Check email for ack

### 8. Verify Email Response

```bash
# Check sent mail
cd /opt/ai-assistant/scripts/mail
python3 -c "from server import list_emails; print(list_emails(limit=5, folder='Sent'))"
```

Should show acknowledgment email sent to Joshua.

### 9. Check State Persistence

```bash
# View current state
cat /var/lib/ai-assistant/state.json | jq .

# Should show:
# - recent_context updated with last email
# - statistics updated
# - personality maintained
```

### 10. Test Voluntary Exit

Wait for controller to run for a few minutes, then:

```bash
# Attach to tmux
tmux attach -t iris

# Send exit command
# (Type in tmux session)
Save state and exit gracefully for context refresh

# Detach and watch
# Press Ctrl-B, then D

# Watch logs
journalctl -u ai-wiggum -f
```

**Expected behavior:**

1. Controller saves state to state.json
2. Controller exits gracefully
3. Wiggum detects exit
4. Wiggum spawns new controller (within 10 seconds)
5. New controller loads state.json and resumes

---

## Monitoring and Health Checks

### 1. Service Health

```bash
# Check service status
systemctl status ai-wiggum

# Expected: Active: active (running)
```

### 2. Controller Health

```bash
# Check tmux session exists
tmux ls | grep iris

# Expected: iris: 1 windows (created ...)
```

### 3. State File Health

```bash
# Verify state file is valid JSON
cat /var/lib/ai-assistant/state.json | jq . > /dev/null && echo "✓ State file valid"

# Check state file size (should be reasonable)
ls -lh /var/lib/ai-assistant/state.json

# Check last modified (should be recent if controller is active)
stat /var/lib/ai-assistant/state.json | grep Modify
```

### 4. Database Health

```bash
# Check database integrity
sqlite3 ~/memory/iris.db "PRAGMA integrity_check;"

# Expected: ok
```

### 5. Email Monitoring

```bash
# Check if controller is monitoring email
# (Attach to tmux and look for email check logs)
tmux attach -t iris

# Or check logs
journalctl -u ai-wiggum -n 50 | grep -i email
```

### 6. Resource Usage

```bash
# Check memory usage
ps aux | grep -E "wiggum|claude-code|iris"

# Expected:
# - wiggum.sh: ~5MB
# - claude-code (controller): 200-500MB
# - claude-code (worker, if active): 200-500MB
```

### 7. Disk Usage

```bash
# Check state directory
du -sh /var/lib/ai-assistant

# Check logs
du -sh /var/log/ai-assistant

# Check database
du -sh ~/memory/iris.db
```

### 8. Log Health

```bash
# View recent logs
journalctl -u ai-wiggum -n 100

# Check for errors
journalctl -u ai-wiggum | grep -i error

# Check for crashes
journalctl -u ai-wiggum | grep -i crash
```

### 9. Automated Health Check Script

Create a health check script:

```bash
cat > /opt/ai-assistant/scripts/health/health_check.sh << 'EOF'
#!/bin/bash

echo "=== Iris + Wiggum Health Check ==="
echo "Date: $(date)"
echo

# Service status
echo "Service Status:"
systemctl is-active ai-wiggum && echo "✓ Service running" || echo "✗ Service not running"

# Tmux session
echo "Controller Status:"
tmux has-session -t iris 2>/dev/null && echo "✓ Controller running" || echo "✗ Controller not running"

# State file
echo "State File:"
test -f /var/lib/ai-assistant/state.json && echo "✓ State file exists" || echo "✗ State file missing"
cat /var/lib/ai-assistant/state.json | jq . > /dev/null 2>&1 && echo "✓ State file valid JSON" || echo "✗ State file corrupted"

# Database
echo "Database:"
test -f ~/memory/iris.db && echo "✓ Database exists" || echo "✗ Database missing"

# Resource usage
echo "Resource Usage:"
ps aux | grep -E "wiggum|claude-code" | grep -v grep | awk '{print "  " $11 ": " $6/1024 " MB"}'

echo
echo "=== Health Check Complete ==="
EOF

chmod +x /opt/ai-assistant/scripts/health/health_check.sh
```

Run health check:

```bash
/opt/ai-assistant/scripts/health/health_check.sh
```

### 10. Set Up Cron Monitoring (Optional)

```bash
# Add to crontab
crontab -e

# Add this line:
# Run health check every hour, log results
0 * * * * /opt/ai-assistant/scripts/health/health_check.sh >> /var/log/ai-assistant/health.log 2>&1
```

---

## Rollback Procedure

If deployment fails or issues arise, follow this rollback procedure.

### 1. Stop Production Service

```bash
sudo systemctl stop ai-wiggum
sudo systemctl disable ai-wiggum
```

### 2. Kill Controller

```bash
tmux kill-session -t iris 2>/dev/null
```

### 3. Restore Backups

```bash
# Find latest backup
ls -lt ~/iris/state.json.backup* | head -1
ls -lt ~/memory/iris.db.backup* | head -1

# Restore state file (if needed)
cp ~/iris/state.json.backup.YYYYMMDD_HHMMSS ~/iris/state.json

# Restore database (if needed)
cp ~/memory/iris.db.backup.YYYYMMDD_HHMMSS ~/memory/iris.db
```

### 4. Restart Development Version

```bash
# If you had a development version running
cd ~/iris
./wiggum.sh &
```

### 5. Verify Rollback

```bash
# Check tmux session
tmux ls

# Check state
cat ~/iris/state.json | jq .

# Check database
sqlite3 ~/memory/iris.db "SELECT COUNT(*) FROM tasks;"
```

### 6. Document Rollback Reason

```bash
echo "$(date): Rolled back deployment. Reason: [describe issue]" >> ~/iris/deployment.log
```

### 7. Investigate Issues

Before attempting redeployment:

1. Review logs: `journalctl -u ai-wiggum -n 500`
2. Check for errors in state.json
3. Verify file permissions
4. Test components individually
5. Re-run test suite: `cd ~/iris/tests && ./run_all_tests.sh`

---

## Post-Deployment Checklist

After successful deployment, complete this checklist:

### Immediate (Day 1)

- [ ] Service is running: `systemctl status ai-wiggum`
- [ ] Controller is running: `tmux ls | grep iris`
- [ ] Test email sent and acknowledged
- [ ] State file updating regularly
- [ ] Logs are clean (no errors)
- [ ] Resource usage is normal (<1GB total)
- [ ] Email monitoring is working

### First Week

- [ ] Voluntary exit/restart cycle tested
- [ ] Crash recovery tested (kill controller, verify respawn)
- [ ] Multiple tasks completed successfully
- [ ] Email from unknown sender tested (dragon response)
- [ ] Worker subagent spawned successfully
- [ ] Database growing with task/email records
- [ ] No memory leaks observed
- [ ] No disk space issues

### First Month

- [ ] Long-term stability confirmed (30+ days uptime)
- [ ] State persistence verified across multiple restarts
- [ ] Self-notes accumulating appropriately
- [ ] Task completion rate is acceptable
- [ ] Email response time is acceptable
- [ ] Resource usage stable
- [ ] Logs manageable (log rotation working)
- [ ] Backup strategy working

### Monitoring Setup

- [ ] Health check script running (cron or manual)
- [ ] Log rotation configured
- [ ] Disk usage monitoring set up
- [ ] Alert for service down (optional)
- [ ] Performance baseline established

### Documentation

- [ ] Production paths documented
- [ ] Operational procedures tested
- [ ] Troubleshooting guide reviewed
- [ ] Team trained on monitoring/intervention
- [ ] Rollback procedure tested

### Optimization

- [ ] Voluntary exit thresholds tuned
- [ ] Email poll frequency optimized
- [ ] Resource limits validated
- [ ] Performance acceptable
- [ ] Self-notes reviewed and pruned if needed

---

## Common Deployment Issues

### Issue: Service won't start

**Symptoms:** `systemctl start ai-wiggum` fails

**Diagnosis:**
```bash
# Check service status
systemctl status ai-wiggum -l

# Check logs
journalctl -u ai-wiggum -n 50
```

**Solutions:**

1. **File not found:**
   - Verify `/opt/ai-assistant/wiggum.sh` exists
   - Check paths in service file
   - Verify permissions: `chmod +x /opt/ai-assistant/wiggum.sh`

2. **Permission denied:**
   - Check ownership: `sudo chown claude:claude /opt/ai-assistant -R`
   - Verify user `claude` exists

3. **Syntax error:**
   - Test script manually: `bash -x /opt/ai-assistant/wiggum.sh`

### Issue: Controller crashes immediately

**Symptoms:** Tmux session starts but dies immediately

**Diagnosis:**
```bash
# Attach to see crash
tmux attach -t iris

# Check logs
journalctl -u ai-wiggum -n 100
```

**Solutions:**

1. **Prompt file not found:**
   - Verify `/opt/ai-assistant/prompts/iris.md` exists
   - Check path in wiggum.sh

2. **State file corrupted:**
   - Check JSON validity: `cat /var/lib/ai-assistant/state.json | jq .`
   - Restore backup or create new: `echo '{}' > /var/lib/ai-assistant/state.json`

3. **Missing dependencies:**
   - Check Python imports: `python3 -c "import json, sqlite3, pathlib"`
   - Reinstall if needed

### Issue: Email not being processed

**Symptoms:** Emails arrive but no acknowledgment sent

**Diagnosis:**
```bash
# Test email tools
cd /opt/ai-assistant/scripts/mail
python3 -c "from server import check_new_emails; print(check_new_emails())"

# Attach to controller and watch
tmux attach -t iris
```

**Solutions:**

1. **Email tools not working:**
   - Check mailbox permissions
   - Verify email server configuration
   - Test email tools directly

2. **Controller not monitoring:**
   - Check controller prompt has email monitoring loop
   - Verify paths to email tools in iris.md
   - Restart controller

3. **Email watchdog not running:**
   - Check if watchdog process exists
   - Restart controller to spawn new watchdog

### Issue: State file not updating

**Symptoms:** state.json hasn't changed in a while

**Diagnosis:**
```bash
# Check last modified time
stat /var/lib/ai-assistant/state.json

# Check file permissions
ls -l /var/lib/ai-assistant/state.json
```

**Solutions:**

1. **Permission issue:**
   - Fix permissions: `sudo chown claude:claude /var/lib/ai-assistant/state.json`

2. **Controller not saving:**
   - Attach to controller and check for errors
   - Verify state_manager.py is working: `python3 -c "from state_manager import save_state; save_state({'test': 'data'})"`

3. **Disk full:**
   - Check disk space: `df -h`
   - Clean up logs if needed

---

## Deployment Checklist Summary

Use this quick checklist for deployment:

```
Pre-Deployment:
[ ] All tests pass (156 tests)
[ ] Validation checklist complete (148 items)
[ ] Dependencies verified
[ ] Backups created

File Migration:
[ ] Production directories created
[ ] Files copied to /opt/ai-assistant/
[ ] Paths updated in config files
[ ] Scripts executable
[ ] Ownership set to claude:claude

Service Installation:
[ ] Service file in /etc/systemd/system/
[ ] systemctl daemon-reload run
[ ] Service enabled
[ ] Service configuration verified

Database Setup:
[ ] Database exists or will be created
[ ] Database connection tested
[ ] Schema initialized
[ ] Tables verified

Email Configuration:
[ ] Email tools working
[ ] Test email sent successfully
[ ] Authorized senders configured
[ ] Email monitoring tested

First Run:
[ ] Initial state.json created
[ ] Service started
[ ] Tmux session running
[ ] Controller initialized
[ ] Test email sent and acknowledged
[ ] State persistence verified
[ ] Voluntary exit tested

Monitoring:
[ ] Health checks passing
[ ] Logs clean
[ ] Resource usage normal
[ ] Email monitoring working

Post-Deployment:
[ ] Documentation updated
[ ] Team notified
[ ] Monitoring set up
[ ] First week verification planned
```

---

## Next Steps After Deployment

1. **Monitor for 24 hours:**
   - Check logs frequently
   - Watch for errors
   - Verify normal operation

2. **Test all workflows:**
   - Email task assignment
   - Worker spawning
   - Voluntary exit/restart
   - Crash recovery
   - Unknown sender protocol

3. **Establish baselines:**
   - Typical resource usage
   - Email response time
   - Task completion time
   - State file size

4. **Set up routine monitoring:**
   - Daily health checks
   - Weekly log review
   - Monthly optimization

5. **Document any issues:**
   - Add to troubleshooting guide
   - Update operations manual
   - Share with team

---

## Support

For deployment issues:

1. **Check logs:** `journalctl -u ai-wiggum -n 100`
2. **Review this guide:** Troubleshooting section
3. **Check operations manual:** [OPERATIONS_MANUAL.md](OPERATIONS_MANUAL.md)
4. **Run health check:** `/opt/ai-assistant/scripts/health/health_check.sh`

---

**Deployment Guide Complete**

**Version:** 1.0
**Last Updated:** February 16, 2026
**Status:** Production-ready
