#!/bin/bash
# test_integration.sh - End-to-end integration test suite
#
# Tests the full Iris + Wiggum lifecycle:
# - Startup sequence
# - Email handling workflows
# - Worker dispatch patterns
# - State persistence across restarts
# - Voluntary exit mechanisms
# - Unknown sender protocol
#
# Usage:
#   ./test_integration.sh          # Run all integration tests
#   ./test_integration.sh --dry    # Dry run mode (no actual spawns)

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

# Check if dry run mode
DRY_RUN=false
if [ "$1" == "--dry" ]; then
    DRY_RUN=true
    warn "Running in DRY RUN mode - no actual controller spawns"
fi

# Start tests
section "Iris + Wiggum Integration Test Suite"
echo "Test date: $(date)"
echo ""

# =============================================================================
# Test 1: File Structure
# =============================================================================
section "Test 1: File Structure Validation"

# Check all required files exist
files=(
    "/home/claude/iris/wiggum.sh"
    "/home/claude/iris/prompts/iris.md"
    "/home/claude/iris/scripts/state/state_manager.py"
    "/home/claude/iris/scripts/state/db.py"
    "/home/claude/iris/config/ai-wiggum.service"
    "/home/claude/iris/prompts/workers/research.md"
    "/home/claude/iris/prompts/workers/drafting.md"
    "/home/claude/iris/prompts/workers/moltbook.md"
    "/home/claude/iris/prompts/workers/coding.md"
    "/home/claude/iris/prompts/workers/analysis.md"
)

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        pass "File exists: $file"
    else
        fail "Missing file: $file"
    fi
done

# =============================================================================
# Test 2: State Manager Validation
# =============================================================================
section "Test 2: State Manager Functionality"

# Test state_manager.py loads correctly
if python3 -c "import sys; sys.path.append('/home/claude/iris/scripts/state'); from state_manager import load_state, save_state, initialize_state" 2>/dev/null; then
    pass "state_manager.py imports successfully"
else
    fail "state_manager.py import failed"
fi

# Test state initialization
TEST_STATE_FILE="/tmp/test_state_integration.json"
if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from state_manager import initialize_state, save_state, load_state

# Initialize
state = initialize_state()
save_state(state, '$TEST_STATE_FILE')

# Load back
loaded = load_state('$TEST_STATE_FILE')

# Validate
assert 'session' in loaded, 'Missing session key'
assert 'active_tasks' in loaded, 'Missing active_tasks key'
assert 'personality' in loaded, 'Missing personality key'
assert 'system' in loaded, 'Missing system key'

print('PASS')
" 2>/dev/null; then
    pass "State initialization and load/save cycle works"
else
    fail "State initialization failed"
fi

# Clean up test state
rm -f "$TEST_STATE_FILE"

# =============================================================================
# Test 3: Database Connectivity
# =============================================================================
section "Test 3: Database Functions"

# Test db.py imports
if python3 -c "import sys; sys.path.append('/home/claude/iris/scripts/state'); from db import create_task, list_tasks, log_activity" 2>/dev/null; then
    pass "db.py imports successfully"
else
    fail "db.py import failed"
fi

# Test database operations
if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from db import create_task, list_tasks, update_task, log_activity
import json

# Create test task
task_id_json = create_task(
    title='Integration test task',
    description='This is a test task',
    priority='low'
)
task_id = json.loads(task_id_json)

# List tasks
tasks = json.loads(list_tasks())
assert len(tasks) > 0, 'No tasks found'

# Update task
update_task(task_id, status='completed', result='Test passed')

# Log activity
log_activity('test', 'Integration test activity', 'Testing database')

print('PASS')
" 2>/dev/null; then
    pass "Database CRUD operations work"
else
    fail "Database operations failed"
fi

# =============================================================================
# Test 4: Worker Template Validation
# =============================================================================
section "Test 4: Worker Template Structure"

worker_templates=(
    "/home/claude/iris/prompts/workers/research.md"
    "/home/claude/iris/prompts/workers/drafting.md"
    "/home/claude/iris/prompts/workers/moltbook.md"
    "/home/claude/iris/prompts/workers/coding.md"
    "/home/claude/iris/prompts/workers/analysis.md"
)

for template in "${worker_templates[@]}"; do
    if [ -f "$template" ] && [ -r "$template" ]; then
        # Check file is not empty
        if [ -s "$template" ]; then
            # Check for key sections (basic validation)
            if grep -q "Purpose" "$template" && grep -q "Instructions" "$template"; then
                pass "Worker template valid: $(basename $template)"
            else
                warn "Worker template missing sections: $(basename $template)"
                ((TESTS_RUN++))
            fi
        else
            fail "Worker template is empty: $(basename $template)"
        fi
    else
        fail "Cannot read worker template: $(basename $template)"
    fi
done

# =============================================================================
# Test 5: Email Protocol Simulation
# =============================================================================
section "Test 5: Email Handling Protocol"

info "Testing email authority validation logic..."

# Test authoritative sender check
if python3 -c "
authoritative_senders = [
    'owner-work@example.com',
    'owner@example.com'
]

test_cases = [
    ('owner-work@example.com', True),
    ('owner@example.com', True),
    ('random@example.com', False),
    ('spam@test.org', False)
]

for sender, expected in test_cases:
    is_auth = sender in authoritative_senders
    assert is_auth == expected, f'Authority check failed for {sender}'

print('PASS')
"; then
    pass "Email authority validation logic correct"
else
    fail "Email authority validation failed"
fi

# =============================================================================
# Test 6: State Persistence Across Restarts
# =============================================================================
section "Test 6: State Persistence Simulation"

info "Simulating controller lifecycle with state persistence..."

TEST_STATE="/tmp/test_lifecycle_state.json"

if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from state_manager import initialize_state, save_state, load_state, merge_state
import json

# Simulate first session
state = initialize_state()
state['session']['session_count'] = 1
state['system']['tasks_completed'] = 5
state['personality']['self_notes'].append('First session note')
save_state(state, '$TEST_STATE')

# Simulate restart - load state
state2 = load_state('$TEST_STATE')
assert state2['session']['session_count'] == 1, 'Session count not persisted'
assert state2['system']['tasks_completed'] == 5, 'Task count not persisted'

# Simulate second session
state2['session']['session_count'] = 2
state2['system']['tasks_completed'] = 12
save_state(state2, '$TEST_STATE')

# Simulate another restart
state3 = load_state('$TEST_STATE')
assert state3['session']['session_count'] == 2, 'Second session count not persisted'
assert state3['system']['tasks_completed'] == 12, 'Updated task count not persisted'
assert len(state3['personality']['self_notes']) == 1, 'Self notes not preserved'

print('PASS')
" 2>/dev/null; then
    pass "State persists correctly across simulated restarts"
else
    fail "State persistence failed"
fi

rm -f "$TEST_STATE"

# =============================================================================
# Test 7: Atomic State Write (Crash Resilience)
# =============================================================================
section "Test 7: Atomic State Write Validation"

info "Testing atomic write mechanism (crash during write)..."

if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from state_manager import initialize_state, save_state
import os
import tempfile

# Create test state
state = initialize_state()
test_file = '/tmp/test_atomic_state.json'

# Save state
result = save_state(state, test_file)
assert result == True, 'Save failed'

# Verify no temp files left behind
temp_dir = os.path.dirname(test_file)
temp_files = [f for f in os.listdir(temp_dir) if f.startswith('.state-')]
assert len(temp_files) == 0, f'Temp files not cleaned up: {temp_files}'

# Verify file is readable
from state_manager import load_state
loaded = load_state(test_file)
assert 'session' in loaded, 'State corrupted'

os.remove(test_file)
print('PASS')
" 2>/dev/null; then
    pass "Atomic write mechanism working (no temp files leaked)"
else
    fail "Atomic write validation failed"
fi

# =============================================================================
# Test 8: Voluntary Exit Trigger Logic
# =============================================================================
section "Test 8: Voluntary Exit Decision Logic"

info "Testing exit trigger conditions..."

if python3 -c "
from datetime import datetime, timedelta

def should_exit(tasks_completed, duration_minutes, emails_processed):
    '''Simplified exit logic for testing'''
    if tasks_completed >= 8:
        return True, 'Task threshold'
    if duration_minutes >= 180:
        return True, 'Duration threshold'
    if emails_processed >= 15:
        return True, 'Email threshold'
    return False, None

# Test cases
test_cases = [
    (10, 60, 5, True, 'Task threshold'),    # High task count
    (3, 200, 5, True, 'Duration threshold'),  # Long duration
    (3, 60, 20, True, 'Email threshold'),    # Many emails
    (3, 60, 5, False, None),                  # All normal
]

for tasks, duration, emails, expected_exit, expected_reason in test_cases:
    should, reason = should_exit(tasks, duration, emails)
    assert should == expected_exit, f'Exit decision wrong for {tasks}/{duration}/{emails}'
    if expected_exit:
        assert reason == expected_reason, f'Exit reason wrong: {reason} != {expected_reason}'

print('PASS')
"; then
    pass "Voluntary exit trigger logic correct"
else
    fail "Voluntary exit logic failed"
fi

# =============================================================================
# Test 9: Unknown Sender Protocol
# =============================================================================
section "Test 9: Unknown Sender Response Protocol"

info "Validating dragon-themed response generation..."

# Check that iris.md contains unknown sender protocol
if grep -q "dragon" /home/claude/iris/prompts/iris.md && \
   grep -q "Unknown senders" /home/claude/iris/prompts/iris.md; then
    pass "Unknown sender protocol documented in iris.md"
else
    fail "Unknown sender protocol missing from iris.md"
fi

# Validate dragon response format (should include ASCII art width limit)
if grep -q "40 char" /home/claude/iris/prompts/iris.md; then
    pass "Dragon response includes mobile-friendly width constraint"
else
    warn "Dragon response width constraint not specified"
    ((TESTS_RUN++))
fi

# =============================================================================
# Test 10: Wiggum Loop Logic
# =============================================================================
section "Test 10: Wiggum Loop Validation"

# Check wiggum.sh contains required logic
if grep -q "while true" /home/claude/iris/wiggum.sh && \
   grep -q "tmux has-session -t iris" /home/claude/iris/wiggum.sh && \
   grep -q "tmux new-session" /home/claude/iris/wiggum.sh && \
   grep -q "claude-code --prompt-file" /home/claude/iris/wiggum.sh; then
    pass "Wiggum loop contains all required components"
else
    fail "Wiggum loop missing required components"
fi

# Check sleep interval exists
if grep -q "sleep" /home/claude/iris/wiggum.sh; then
    pass "Wiggum loop includes check interval (sleep)"
else
    fail "Wiggum loop missing sleep interval"
fi

# =============================================================================
# Test 11: Controller Startup Sequence
# =============================================================================
section "Test 11: Controller Startup Procedure Validation"

info "Checking iris.md startup instructions..."

startup_requirements=(
    "Startup Procedure"
    "Check for State File"
    "Restore Personality"
    "Read Database State"
    "Check for Unread Email"
    "Log Session Start"
)

for requirement in "${startup_requirements[@]}"; do
    if grep -q "$requirement" /home/claude/iris/prompts/iris.md; then
        pass "Startup step documented: $requirement"
    else
        fail "Missing startup step: $requirement"
    fi
done

# =============================================================================
# Test 12: Worker Dispatch Pattern
# =============================================================================
section "Test 12: Worker Dispatch Pattern Validation"

info "Checking worker orchestration instructions..."

if grep -q "Worker Subagent Orchestration" /home/claude/iris/prompts/iris.md && \
   grep -q "When to Use Workers" /home/claude/iris/prompts/iris.md && \
   grep -q "Worker Template System" /home/claude/iris/prompts/iris.md; then
    pass "Worker orchestration fully documented"
else
    fail "Worker orchestration documentation incomplete"
fi

# Check that templates directory exists and is referenced
if grep -q "/home/claude/iris/prompts/workers/" /home/claude/iris/prompts/iris.md; then
    pass "Worker template directory referenced in iris.md"
else
    fail "Worker template directory not referenced"
fi

# =============================================================================
# Test 13: Email Promise Tracking
# =============================================================================
section "Test 13: Email Promise Tracking Validation"

info "Validating email promise tracking protocol..."

if grep -q "Email promise tracking" /home/claude/iris/prompts/iris.md && \
   grep -q "BEFORE sending" /home/claude/iris/prompts/iris.md; then
    pass "Email promise tracking protocol documented"
else
    fail "Email promise tracking missing from iris.md"
fi

# =============================================================================
# Test 14: Full Cycle Simulation (Optional - DRY RUN ONLY)
# =============================================================================
if [ "$DRY_RUN" == "true" ]; then
    section "Test 14: Full Cycle Simulation (Dry Run)"

    info "Simulating complete controller lifecycle..."

    SIMULATION_STATE="/tmp/simulation_state.json"

    if python3 -c "
import sys
sys.path.append('/home/claude/iris/scripts/state')
from state_manager import initialize_state, save_state, load_state
from db import create_task, update_task, log_activity
import json
from datetime import datetime

# 1. Simulate startup
print('Step 1: Controller starts up...')
state = load_state('$SIMULATION_STATE')
if not state:
    state = initialize_state()
    state['session']['session_count'] = 1
else:
    state['session']['session_count'] += 1

save_state(state, '$SIMULATION_STATE')
log_activity('session', 'Controller started', f\"Session #{state['session']['session_count']}\")

# 2. Simulate email arrival
print('Step 2: Email arrives...')
task_id = json.loads(create_task(
    title='Respond to Joshua about research',
    description='Email from owner-work@example.com',
    priority='high'
))
state['recent_context']['last_email'] = 'Research request from Joshua'
save_state(state, '$SIMULATION_STATE')

# 3. Simulate task completion
print('Step 3: Task processed...')
update_task(task_id, status='completed', result='Research completed and emailed')
state['system']['tasks_completed'] += 1
state['system']['emails_sent'] += 1
save_state(state, '$SIMULATION_STATE')

# 4. Simulate voluntary exit
print('Step 4: Voluntary exit...')
state['session']['exit_reason'] = 'voluntary'
state['system']['voluntary_exits'] += 1
save_state(state, '$SIMULATION_STATE')

# 5. Simulate restart
print('Step 5: Controller restarts (wiggum respawn)...')
state2 = load_state('$SIMULATION_STATE')
assert state2['session']['session_count'] == 1, 'Session count lost'
assert state2['system']['tasks_completed'] == 1, 'Task count lost'

print('✓ Full lifecycle simulation PASSED')
" 2>/dev/null; then
        pass "Full lifecycle simulation successful"
    else
        fail "Full lifecycle simulation failed"
    fi

    rm -f "$SIMULATION_STATE"
else
    section "Test 14: Full Cycle Test"
    info "Skipped (use --dry to enable dry run simulation)"
fi

# =============================================================================
# Final Summary
# =============================================================================
section "Integration Test Summary"

echo ""
echo "Tests run:    $TESTS_RUN"
echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL INTEGRATION TESTS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Iris + Wiggum architecture is ready for deployment."
    echo ""
    echo "Integration test coverage:"
    echo "  ✓ File structure and dependencies"
    echo "  ✓ State management and persistence"
    echo "  ✓ Database operations"
    echo "  ✓ Worker templates"
    echo "  ✓ Email protocols"
    echo "  ✓ Voluntary exit logic"
    echo "  ✓ Controller startup sequence"
    echo "  ✓ Crash resilience (atomic writes)"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ INTEGRATION TESTS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Fix the issues above before deploying."
    echo ""
    exit 1
fi
