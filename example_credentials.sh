#!/usr/bin/env bash
#
# Example credentials/environment setup for the assistant
# Copy this file to ~/.iris/credentials.sh and fill in your actual values
# Then source it before running: source ~/.iris/credentials.sh
#

# Assistant identity
export ASSISTANT_NAME="${ASSISTANT_NAME:-Iris}"
export OWNER_NAME="${OWNER_NAME:-YourName}"
export OWNER_TITLE="${OWNER_TITLE:-Your Name, Your Institution}"

# Postmark API Token (for sending email)
# Get this from https://account.postmarkapp.com/
export POSTMARK_API_TOKEN="your-postmark-api-token-here"

# Owner email addresses
export OWNER_EMAIL="${OWNER_EMAIL:-owner@example.com}"
export OWNER_UCL_EMAIL="${OWNER_UCL_EMAIL:-owner-work@example.com}"

# Moltbook API credentials (optional - only if using Moltbook integration)
# These should be in ~/.config/moltbook/credentials.json with format:
# {
#   "email": "your-email@example.com",
#   "password": "your-password"
# }

# Mail server domain (customize for your setup)
export IRIS_DOMAIN="${IRIS_DOMAIN:-example.com}"
export IRIS_EMAIL="${IRIS_EMAIL:-iris@${IRIS_DOMAIN}}"

# Database path (optional - defaults to ~/iris/memory/iris.db)
export IRIS_DB_PATH="${IRIS_DB_PATH:-$HOME/iris/memory/iris.db}"

# State file path (optional - defaults to ~/iris/state.json)
export IRIS_STATE_PATH="${IRIS_STATE_PATH:-$HOME/iris/state.json}"

echo "✓ ${ASSISTANT_NAME} credentials loaded"
echo "  POSTMARK_API_TOKEN: ${POSTMARK_API_TOKEN:0:8}..."
echo "  IRIS_EMAIL: $IRIS_EMAIL"
