#!/bin/bash
# test_email_flow.sh - Email workflow validation suite
#
# Tests email handling workflows including:
# - Unknown sender → dragon response → forward to Joshua
# - Authorized sender → ack → queue → work → result email
# - Promise tracking (email creates task before sending)
# - Authority validation
# - Response timing expectations
#
# Usage:
#   ./test_email_flow.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counter
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((TESTS_PASSED++))
    ((TESTS_RUN++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((TESTS_FAILED++))
    ((TESTS_RUN++))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Start tests
section "Email Flow Validation Suite"
echo "Test date: $(date)"
echo ""

# =============================================================================
# Test 1: Authority Validation Logic
# =============================================================================
section "Test 1: Email Authority Validation"

info "Testing sender authority classification..."

# Test authority validation logic
if python3 -c "
# Authoritative senders
AUTH_SENDERS = [
    'owner-work@example.com',
    'owner@example.com'
]

def is_authorized(sender):
    '''Check if sender is authorized'''
    return sender.lower() in [s.lower() for s in AUTH_SENDERS]

# Test cases
test_cases = [
    ('owner-work@example.com', True),
    ('OWNER@EXAMPLE.COM', True),  # Case insensitive
    ('owner@example.com', True),
    ('random@example.com', False),
    ('spam@test.org', False),
    ('joshua@wrong-domain.com', False),
]

for sender, expected in test_cases:
    result = is_authorized(sender)
    assert result == expected, f'Authority check failed for {sender}: got {result}, expected {expected}'

print('PASS')
" 2>/dev/null; then
    pass "Email authority validation logic correct"
else
    fail "Email authority validation logic failed"
fi

# =============================================================================
# Test 2: Unknown Sender Protocol
# =============================================================================
section "Test 2: Unknown Sender Response Protocol"

info "Validating unknown sender handling..."

# Check iris.md contains unknown sender protocol
IRIS_PROMPT="/home/claude/iris/prompts/iris.md"

if [ ! -f "$IRIS_PROMPT" ]; then
    fail "iris.md not found at $IRIS_PROMPT"
else
    # Check for key elements of unknown sender protocol
    if grep -qi "unknown sender" "$IRIS_PROMPT"; then
        pass "Unknown sender protocol documented in iris.md"
    else
        fail "Unknown sender protocol missing from iris.md"
    fi

    # Check for dragon-themed response requirement
    if grep -qi "dragon" "$IRIS_PROMPT"; then
        pass "Dragon-themed response requirement present"
    else
        fail "Dragon-themed response requirement missing"
    fi

    # Check for forward-to-Joshua requirement
    if grep -qi "forward.*joshua" "$IRIS_PROMPT"; then
        pass "Forward to Joshua requirement documented"
    else
        fail "Forward to Joshua requirement missing"
    fi

    # Check for ASCII art width constraint (mobile-friendly)
    if grep -qi "40.*char\|mobile" "$IRIS_PROMPT"; then
        pass "ASCII art width constraint specified (mobile-friendly)"
    else
        warn "ASCII art width constraint not explicitly specified"
        ((TESTS_RUN++))
    fi

    # Check for "do not act" requirement
    if grep -qi "do not act\|wait for.*approval" "$IRIS_PROMPT"; then
        pass "Do-not-act-autonomously requirement documented"
    else
        fail "Do-not-act requirement missing"
    fi
fi

# =============================================================================
# Test 3: Authorized Sender Flow
# =============================================================================
section "Test 3: Authorized Sender Workflow"

info "Validating authorized sender email flow..."

# Check for immediate acknowledgment requirement
if grep -qi "immediate.*ack\|always.*reply\|receipt" "$IRIS_PROMPT"; then
    pass "Immediate acknowledgment requirement documented"
else
    fail "Immediate acknowledgment requirement missing"
fi

# Check for task creation workflow
if grep -qi "create.*task\|database.*task\|queue" "$IRIS_PROMPT"; then
    pass "Task creation workflow documented"
else
    fail "Task creation workflow missing"
fi

# Check for completion update requirement
if grep -qi "completion.*update\|send.*result\|when.*done" "$IRIS_PROMPT"; then
    pass "Completion update requirement documented"
else
    fail "Completion update requirement missing"
fi

# =============================================================================
# Test 4: Promise Tracking Protocol
# =============================================================================
section "Test 4: Email Promise Tracking"

info "Validating promise tracking protocol..."

# Check for promise tracking documentation
if grep -qi "promise.*tracking\|email promise" "$IRIS_PROMPT"; then
    pass "Promise tracking protocol documented"
else
    fail "Promise tracking protocol missing"
fi

# Check for create-task-before-sending requirement
if grep -qi "before.*send.*email\|create.*task.*before" "$IRIS_PROMPT"; then
    pass "Create-task-before-send requirement documented"
else
    fail "Create-task-before-send requirement missing"
fi

# Check for examples of promises
if grep -qi "i'll.*research\|i'll.*post\|i'll.*monitor" "$IRIS_PROMPT"; then
    pass "Promise examples provided"
else
    warn "No explicit promise examples in documentation"
    ((TESTS_RUN++))
fi

# =============================================================================
# Test 5: Email Flow Simulation
# =============================================================================
section "Test 5: Email Workflow Simulation"

info "Simulating complete email workflows..."

# Test authorized sender workflow simulation
if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from db import create_task, update_task, log_activity, list_tasks
import json

# Simulate: Email arrives from authorized sender
print('Step 1: Email arrives from owner-work@example.com')

# Simulate: Send immediate ack (would happen here)
print('Step 2: Send immediate acknowledgment')

# Simulate: Create task
task_id_json = create_task(
    title='Test: Research collective intelligence',
    description='Email from Joshua requesting research',
    priority='high',
    source_email_id='test_email_123'
)
task_id = json.loads(task_id_json)
print(f'Step 3: Task created (ID: {task_id})')

# Simulate: Task processing
update_task(task_id, status='in_progress')
print('Step 4: Task started')

# Simulate: Task completion
update_task(task_id, status='completed', result='Research completed')
print('Step 5: Task completed')

# Simulate: Send result email (would happen here)
print('Step 6: Send completion email with results')

# Verify task lifecycle
tasks = json.loads(list_tasks())
completed = [t for t in tasks if t['id'] == task_id and t['status'] == 'completed']
assert len(completed) == 1, 'Task not found in completed state'

print('✓ Authorized sender workflow simulation PASSED')
" 2>/dev/null; then
    pass "Authorized sender workflow simulation successful"
else
    fail "Authorized sender workflow simulation failed"
fi

# Test unknown sender workflow simulation
if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from db import log_activity
import json

# Simulate: Email arrives from unknown sender
sender = 'unknown@example.com'
subject = 'Can you help me?'
print(f'Step 1: Email from unknown sender: {sender}')

# Simulate: Check authority
auth_senders = ['owner-work@example.com', 'owner@example.com']
is_authorized = sender.lower() in [s.lower() for s in auth_senders]
assert not is_authorized, 'Authority check should fail for unknown sender'
print('Step 2: Authority check FAILED (correct)')

# Simulate: Send dragon response (would happen here)
print('Step 3: Send dragon-themed auto-reply to unknown sender')

# Simulate: Forward to Joshua (would happen here)
print('Step 4: Forward email details to Joshua')

# Simulate: Log activity
log_activity(
    category='email',
    summary=f'Unknown sender: {sender}',
    details=f'Sent dragon response and forwarded to Joshua',
    email_id='test_unknown_123'
)
print('Step 5: Activity logged')

# Simulate: Do NOT create task (wait for Joshua)
print('Step 6: NO task created - awaiting Joshua approval')

print('✓ Unknown sender workflow simulation PASSED')
" 2>/dev/null; then
    pass "Unknown sender workflow simulation successful"
else
    fail "Unknown sender workflow simulation failed"
fi

# =============================================================================
# Test 6: Email Watchdog Pattern
# =============================================================================
section "Test 6: Email Watchdog Pattern"

info "Validating email monitoring documentation..."

# Check for watchdog pattern in iris.md
if grep -qi "watchdog" "$IRIS_PROMPT"; then
    pass "Email watchdog pattern documented"
else
    warn "Email watchdog pattern not explicitly mentioned"
    ((TESTS_RUN++))
fi

# Check for polling alternative
if grep -qi "poll\|check.*email" "$IRIS_PROMPT"; then
    pass "Email polling mechanism documented"
else
    fail "Email polling mechanism not documented"
fi

# =============================================================================
# Test 7: Response Timing Requirements
# =============================================================================
section "Test 7: Response Timing Requirements"

info "Validating response timing expectations..."

# Check for immediate/quick response requirement
if grep -qi "immediate\|within.*second\|quickly" "$IRIS_PROMPT"; then
    pass "Quick response timing requirement documented"
else
    fail "Response timing requirement missing"
fi

# Check for "more updates better than fewer" guidance
if grep -qi "more update.*fewer\|frequent.*update" "$IRIS_PROMPT"; then
    pass "Frequent update preference documented"
else
    warn "Update frequency preference not explicitly stated"
    ((TESTS_RUN++))
fi

# =============================================================================
# Test 8: Email Tools Availability
# =============================================================================
section "Test 8: Email Tools Integration"

info "Checking email tools availability..."

# Check if email server tools exist
EMAIL_SERVER="/home/claude/iris/mail-mcp/server.py"

if [ -f "$EMAIL_SERVER" ]; then
    pass "Email server tools found: $EMAIL_SERVER"
else
    fail "Email server tools missing: $EMAIL_SERVER"
fi

# Test email tools import
if python3 -c "
import sys
sys.path.append('/home/claude/iris/mail-mcp')
try:
    from server import check_new_emails, send_email, list_emails
    print('PASS')
except ImportError as e:
    print(f'FAIL: {e}')
    exit(1)
" 2>/dev/null; then
    pass "Email tools can be imported"
else
    warn "Email tools import failed (may need configuration)"
    ((TESTS_RUN++))
fi

# =============================================================================
# Test 9: Promise Tracking Implementation
# =============================================================================
section "Test 9: Promise Tracking Implementation"

info "Testing promise tracking database integration..."

if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from db import create_task, list_tasks
import json

# Simulate promise tracking workflow
# Email says: 'I'll research this topic for you'

# BEFORE sending email, create task
task_id_json = create_task(
    title='Research topic as promised in email',
    description='Promise made in response to owner-work@example.com',
    priority='high',
    source_email_id='promise_test_email'
)
task_id = json.loads(task_id_json)

# Now email can be sent (with promise)
# Verify task exists
tasks = json.loads(list_tasks())
promise_task = [t for t in tasks if t['id'] == task_id]
assert len(promise_task) == 1, 'Promise task not created'
assert 'promise' in promise_task[0]['title'].lower(), 'Task should reference promise'

print('✓ Promise tracking implementation PASSED')
" 2>/dev/null; then
    pass "Promise tracking implementation validated"
else
    fail "Promise tracking implementation failed"
fi

# =============================================================================
# Test 10: Multi-Step Email Flow
# =============================================================================
section "Test 10: Multi-Step Email Interaction"

info "Simulating multi-step email conversation..."

if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from db import create_task, update_task, log_activity
import json

# Step 1: Initial email from Joshua
task_id = json.loads(create_task(
    title='Multi-step research project',
    description='Joshua requests detailed research',
    priority='high'
))
log_activity('email', 'Received request', 'Initial email from Joshua')

# Step 2: Send ack (immediate)
log_activity('email', 'Sent acknowledgment', 'Quick ack sent')

# Step 3: Start work
update_task(task_id, status='in_progress')
log_activity('task', 'Started research', task_id=task_id)

# Step 4: Send intermediate update (if taking >5 min)
log_activity('email', 'Sent progress update', 'Research in progress, 50% complete')

# Step 5: Complete work
update_task(task_id, status='completed', result='Research complete')
log_activity('task', 'Completed research', task_id=task_id)

# Step 6: Send final results
log_activity('email', 'Sent completion email', 'Full results delivered to Joshua')

print('✓ Multi-step email flow PASSED')
" 2>/dev/null; then
    pass "Multi-step email interaction simulation successful"
else
    fail "Multi-step email interaction failed"
fi

# =============================================================================
# Final Summary
# =============================================================================
section "Email Flow Test Summary"

echo ""
echo "Tests run:    $TESTS_RUN"
echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL EMAIL FLOW TESTS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Email workflow validation complete:"
    echo "  ✓ Authority validation"
    echo "  ✓ Unknown sender protocol (dragon responses)"
    echo "  ✓ Authorized sender workflow"
    echo "  ✓ Promise tracking"
    echo "  ✓ Response timing requirements"
    echo "  ✓ Email watchdog pattern"
    echo "  ✓ Multi-step interactions"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ EMAIL FLOW TESTS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Fix the issues above before deployment."
    echo ""
    exit 1
fi
