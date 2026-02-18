#!/bin/bash
# Wrapper script to load Postmark credentials and start the mail MCP server

# Source credentials
source /home/claude/iris/docs/services/postmark-account.sh

# Execute the Python server
exec python3 /home/claude/iris/mail-mcp/server.py
