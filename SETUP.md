# Iris Setup Guide

This guide walks you through setting up Iris from a fresh clone of the repository.

## Prerequisites

Before you begin, ensure you have:

- Linux server with systemd (Ubuntu 20.04+ or Debian 11+ recommended)
- Python 3.8 or higher
- tmux installed (`sudo apt install tmux`)
- Claude Code CLI installed (or Claude API access)
- A mail server configured (Postfix + Dovecot)
- Postmark API account (free tier available at https://postmarkapp.com)

## Step 1: Clone the Repository

```bash
git clone https://github.com/joshua-a-becker/iris.git
cd iris
```

## Step 2: Set Up Credentials

**IMPORTANT:** Never commit credentials to git. All credentials should be stored in environment variables.

```bash
# Create credentials directory
mkdir -p ~/.iris

# Copy template
cp example_credentials.sh ~/.iris/credentials.sh

# Edit with your actual values
nano ~/.iris/credentials.sh
```

Required credentials:
- **POSTMARK_API_TOKEN**: Get from https://account.postmarkapp.com/
- **IRIS_DOMAIN**: Your mail server domain (e.g., example.com)
- **IRIS_EMAIL**: Iris's email address (e.g., iris@example.com)

Optional (have sensible defaults):
- **IRIS_DB_PATH**: Database location (default: ~/iris/scripts/state/iris.db)
- **IRIS_STATE_PATH**: State file location (default: ~/iris/state.json)

## Step 3: Initialize Database

```bash
# Create database directory
mkdir -p scripts/state

# Initialize database with schema
python3 -c "
import sqlite3
conn = sqlite3.connect('scripts/state/iris.db')
with open('schema.sql', 'r') as f:
    conn.executescript(f.read())
conn.close()
print('Database initialized successfully')
"
```

## Step 4: Configure Mail Server

Iris needs to receive emails. You have two options:

### Option A: Use existing mail server

If you already have Postfix + Dovecot configured, just ensure:
- Iris's email address is configured as a valid recipient
- Mail is delivered to a local mailbox Iris can read

### Option B: Set up mail server from scratch

See `email/mail-server.md` for detailed instructions on:
- Installing Postfix + Dovecot
- Configuring DNS (MX, SPF, DKIM, DMARC)
- Setting up local delivery

## Step 5: Test Setup

```bash
# Load credentials
source ~/.iris/credentials.sh

# Test email sending
python3 -c "
import sys
sys.path.insert(0, './email')
from server import send_email
result = send_email('your-email@example.com', 'Test from Iris', 'This is a test email.')
print(result)
"

# Run test suite
cd tests
./run_all_tests.sh
```

## Step 6: Run Iris Manually (Testing)

```bash
# Load credentials
source ~/.iris/credentials.sh

# Run wiggum loop manually (foreground)
./wiggum.sh
```

In another terminal:
```bash
# Attach to Iris's tmux session
tmux attach -t iris
```

Send a test email to Iris and watch it respond!

## Step 7: Install as Systemd Service (Production)

Once you've tested manually, install as a service:

```bash
# Edit service file to match your paths
nano config/ai-wiggum.service

# Copy to systemd
sudo cp config/ai-wiggum.service /etc/systemd/system/

# Create environment file for credentials
sudo nano /etc/systemd/system/ai-wiggum.service.d/override.conf
```

Add credentials to override.conf:
```ini
[Service]
Environment="POSTMARK_API_TOKEN=your-token-here"
Environment="IRIS_DOMAIN=your-domain.com"
Environment="IRIS_EMAIL=iris@your-domain.com"
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-wiggum
sudo systemctl start ai-wiggum
sudo systemctl status ai-wiggum
```

## Step 8: Verify Operation

```bash
# Check if tmux session exists
tmux ls | grep iris

# Watch logs
sudo journalctl -u ai-wiggum -f

# Attach to session
tmux attach -t iris
```

## Troubleshooting

### Email sending fails

- Check POSTMARK_API_TOKEN is set: `echo $POSTMARK_API_TOKEN`
- Verify Postmark account is active
- Check logs: `sudo journalctl -u ai-wiggum -f`

### Email receiving doesn't work

- Verify mail server is running: `systemctl status postfix`
- Check mailbox permissions: `ls -la /var/mail/`
- Test local delivery: `echo "test" | mail -s "test" claude@localhost`

### Iris doesn't start

- Check Claude CLI is installed: `which claude`
- Verify credentials are loaded: `source ~/.iris/credentials.sh`
- Check database exists: `ls -la scripts/state/iris.db`

### Database errors

- Reinitialize: `rm scripts/state/iris.db` then rerun Step 3
- Check permissions: `ls -la scripts/state/`

## Next Steps

- Read `OPERATIONS_MANUAL.md` for day-to-day management
- See `DEPLOYMENT_GUIDE.md` for production best practices
- Check `README.md` for architecture overview

## Getting Help

- Check the logs: `sudo journalctl -u ai-wiggum -f`
- Attach to tmux: `tmux attach -t iris`
- Review docs in `docs/` directory
- Open an issue on GitHub

## Security Notes

- Never commit credentials to git
- Use systemd override files for environment variables
- Restrict access to credentials files: `chmod 600 ~/.iris/credentials.sh`
- Keep your Postmark API token secret
- Use HTTPS for all web interfaces
- Keep system packages up to date

## File Structure After Setup

```
iris/
├── config/              # Systemd service files
├── docs/                # Documentation
├── email/               # Email handling code
├── memory/              # Database utilities
├── prompts/             # Iris system prompts
├── scripts/             # Core scripts
│   └── state/           # Database and state management
│       └── iris.db      # Main database (created in setup)
├── tests/               # Test suite
├── example_credentials.sh  # Template (do not edit)
├── schema.sql           # Database schema
├── wiggum.sh           # Controller respawn loop
└── state.json          # Runtime state (created by Iris)

~/.iris/
└── credentials.sh      # Your actual credentials (not in git)
```

## Clean Reinstall

If you need to start over:

```bash
cd iris
rm -f scripts/state/iris.db
rm -f state.json
rm -f ~/.iris/credentials.sh

# Then follow setup steps again
```

---

**Last Updated:** 2026-02-16
