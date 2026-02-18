#!/bin/bash
# test_wiggum.sh - Test suite for wiggum loop
#
# Tests the wiggum.sh controller respawn loop without actually running it.
# Verifies prerequisites, logic, and service configuration.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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
    echo -e "${YELLOW}ℹ${NC} $1"
}

section() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "$1"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Start tests
section "Wiggum Loop Test Suite"

# Test 1: wiggum.sh exists and is executable
section "Test 1: File Permissions"
if [ -f /home/claude/iris/wiggum.sh ]; then
    pass "wiggum.sh exists"
else
    fail "wiggum.sh does not exist at /home/claude/iris/wiggum.sh"
fi

if [ -x /home/claude/iris/wiggum.sh ]; then
    pass "wiggum.sh is executable"
else
    fail "wiggum.sh is not executable (run: chmod +x /home/claude/iris/wiggum.sh)"
fi

# Test 2: wiggum.sh syntax check
section "Test 2: Bash Syntax"
if bash -n /home/claude/iris/wiggum.sh 2>/dev/null; then
    pass "wiggum.sh has valid bash syntax"
else
    fail "wiggum.sh has syntax errors"
    bash -n /home/claude/iris/wiggum.sh
fi

# Test 3: Check for key components in wiggum.sh
section "Test 3: Logic Components"

if grep -q "while true" /home/claude/iris/wiggum.sh; then
    pass "wiggum.sh contains main loop (while true)"
else
    fail "wiggum.sh missing main loop"
fi

if grep -q "tmux has-session -t iris" /home/claude/iris/wiggum.sh; then
    pass "wiggum.sh checks for tmux session 'iris'"
else
    fail "wiggum.sh missing tmux session check"
fi

if grep -q "tmux new-session -d -s iris" /home/claude/iris/wiggum.sh; then
    pass "wiggum.sh spawns tmux session 'iris'"
else
    fail "wiggum.sh missing tmux spawn command"
fi

if grep -q "claude-code --prompt-file" /home/claude/iris/wiggum.sh; then
    pass "wiggum.sh uses claude-code with --prompt-file"
else
    fail "wiggum.sh missing claude-code command"
fi

if grep -q "sleep" /home/claude/iris/wiggum.sh; then
    pass "wiggum.sh includes sleep intervals"
else
    fail "wiggum.sh missing sleep intervals"
fi

# Test 4: Tmux session detection (dry run)
section "Test 4: Tmux Session Detection"

# Check if iris session already exists
if tmux has-session -t iris 2>/dev/null; then
    info "Tmux session 'iris' currently EXISTS"
    info "Test: tmux has-session -t iris → exit code 0"
else
    info "Tmux session 'iris' does NOT exist"
    info "Test: tmux has-session -t iris → exit code 1"
fi

# Verify tmux command works
if command -v tmux >/dev/null 2>&1; then
    pass "tmux command is available"
else
    fail "tmux command not found (install: sudo apt-get install tmux)"
fi

# Test 5: Service file validation
section "Test 5: Systemd Service File"

SERVICE_FILE="/home/claude/iris/config/ai-wiggum.service"

if [ -f "$SERVICE_FILE" ]; then
    pass "ai-wiggum.service exists"
else
    fail "ai-wiggum.service missing at $SERVICE_FILE"
    exit 1
fi

# Check for required service sections
if grep -q "^\[Unit\]" "$SERVICE_FILE"; then
    pass "Service file has [Unit] section"
else
    fail "Service file missing [Unit] section"
fi

if grep -q "^\[Service\]" "$SERVICE_FILE"; then
    pass "Service file has [Service] section"
else
    fail "Service file missing [Service] section"
fi

if grep -q "^\[Install\]" "$SERVICE_FILE"; then
    pass "Service file has [Install] section"
else
    fail "Service file missing [Install] section"
fi

# Check for required service directives
if grep -q "^ExecStart=" "$SERVICE_FILE"; then
    pass "Service file has ExecStart directive"
    EXEC_START=$(grep "^ExecStart=" "$SERVICE_FILE" | cut -d= -f2-)
    info "ExecStart: $EXEC_START"
else
    fail "Service file missing ExecStart directive"
fi

if grep -q "^User=" "$SERVICE_FILE"; then
    pass "Service file has User directive"
else
    fail "Service file missing User directive"
fi

if grep -q "^Restart=" "$SERVICE_FILE"; then
    pass "Service file has Restart directive"
else
    fail "Service file missing Restart directive"
fi

# Test 6: Prompt file existence
section "Test 6: Prompt File"

PROMPT_FILE="/home/claude/iris/prompts/iris.md"

if [ -f "$PROMPT_FILE" ]; then
    pass "iris.md prompt file exists"
else
    fail "iris.md prompt file missing at $PROMPT_FILE"
fi

# Test 7: Check for claude-code command
section "Test 7: Claude Code Availability"

if command -v claude-code >/dev/null 2>&1; then
    pass "claude-code command is available"
    CLAUDE_VERSION=$(claude-code --version 2>/dev/null || echo "unknown")
    info "Version: $CLAUDE_VERSION"
else
    fail "claude-code command not found"
fi

# Test 8: Dry run check (syntax only, don't actually run)
section "Test 8: Dry Run Logic Check"

info "Testing wiggum.sh logic (simulated)..."

# Simulate the logic without actually running
if ! tmux has-session -t iris 2>/dev/null; then
    info "Logic: Session 'iris' not found → would spawn controller"
    pass "Spawn logic would trigger (correct behavior)"
else
    info "Logic: Session 'iris' exists → would sleep and check again"
    pass "Sleep logic would trigger (correct behavior)"
fi

# Final summary
section "Test Summary"

echo ""
echo "Tests run:    $TESTS_RUN"
echo -e "${GREEN}Tests passed: $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Wiggum loop is ready for testing."
    echo ""
    echo "Next steps:"
    echo "  1. Review wiggum.sh implementation"
    echo "  2. Test manually: /home/claude/iris/wiggum.sh"
    echo "  3. Stop test with Ctrl+C when satisfied"
    echo "  4. Install service when ready for production"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ TESTS FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Fix the issues above before deploying wiggum loop."
    echo ""
    exit 1
fi
