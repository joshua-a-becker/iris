# Health Monitoring Scripts

**Status:** Placeholder for Phase 2

This directory will contain health monitoring and resource management scripts.

## Purpose

Monitor system resources and prevent runaway processes from crashing the server.

## Planned Scripts

### monitor.py
Main health monitor that runs continuously (likely as systemd service).

**Responsibilities:**
- Monitor all claude-code processes for memory usage
- Kill any process exceeding 3GB RAM (safety limit)
- Monitor disk usage (logs, task outputs, email storage)
- Alert operator if issues detected
- Log system-level events

**Usage:**
```bash
# Run as systemd service (ai-health.service)
python3 /home/claude/iris/scripts/health/monitor.py
```

### alerts.py
Alert system for operator notifications.

**Methods:**
- Email to Joshua (high-priority alerts)
- Log to master_log.md (all alerts)
- System journal (critical errors)

**Alert triggers:**
- Wiggum loop died (systemd should prevent this)
- Controller repeatedly crashing (> 5 crashes in 10 minutes)
- Disk usage > 90%
- Memory pressure (swap usage high)
- Process killed for excessive RAM

### cleanup.py
Periodic cleanup of old files and logs.

**Cleanup targets:**
- Old task checkpoint directories (> 30 days)
- Truncate large log files (keep last 10MB)
- Archive old master_log.md entries (> 90 days)
- Clean up orphaned tmux sessions

**Usage:**
```bash
# Run daily via cron
0 3 * * * /home/claude/iris/scripts/health/cleanup.py
```

### stats.py
System statistics and reporting.

**Reports:**
- Daily summary (tasks completed, emails handled, context refreshes)
- Weekly trends (average task duration, memory usage, etc.)
- Resource usage over time

**Usage:**
```bash
# Generate daily report
python3 /home/claude/iris/scripts/health/stats.py --daily

# Email weekly summary to Joshua
python3 /home/claude/iris/scripts/health/stats.py --weekly --email
```

## Resource Limits

Based on 2-core/4GB RAM server with 8GB swap:

**Normal operation:**
- Wiggum loop: ~5MB (sleeping bash process)
- Controller: 200-500MB (Claude Code instance)
- Worker subagent: 200-500MB (when active)
- Total peak: ~1GB with controller + 1 worker

**Hard limits enforced:**
- Kill any claude-code process > 3GB RAM
- Max 2 concurrent workers (controller + 2 workers = ~1.5GB peak)
- Disk usage alert at 90% full
- Swap usage alert if > 2GB used

## Integration with Systemd

**ai-health.service** (to be created in Phase 2):

```ini
[Unit]
Description=AI Assistant Health Monitor
After=network.target ai-wiggum.service

[Service]
Type=simple
User=claude
WorkingDirectory=/home/claude
ExecStart=/usr/bin/python3 /home/claude/iris/scripts/health/monitor.py
Restart=always
RestartSec=10
MemoryMax=128M

[Install]
WantedBy=multi-user.target
```

## Logging

All health events logged to:
- System journal: `journalctl -u ai-health -f`
- Master log: `/home/claude/master_log.md`
- Health log: `/home/claude/iris/scripts/health/health.log`

## Phase 2 Implementation

Priority order:
1. **monitor.py** - Basic resource monitoring (essential for safety)
2. **alerts.py** - Operator notifications (important for awareness)
3. **cleanup.py** - Disk space management (prevents long-term issues)
4. **stats.py** - Reporting (nice to have, not critical)

---

**See revised-architecture.md lines 135-143** for health monitor design details.
