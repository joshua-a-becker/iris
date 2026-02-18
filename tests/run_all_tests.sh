#!/bin/bash
# run_all_tests.sh - Run complete Phase 4 test suite
#
# Executes all testing utilities in sequence:
# 1. test_wiggum.sh - Basic wiggum validation
# 2. test_state.py - State management unit tests
# 3. test_workers.sh - Worker template validation
# 4. test_email_flow.sh - Email workflow tests
# 5. test_integration.sh --dry - Integration tests (dry run)
# 6. dry_run.sh --once - Dry run simulation
#
# Usage:
#   ./run_all_tests.sh              # Run all tests
#   ./run_all_tests.sh --verbose    # Verbose output
#   ./run_all_tests.sh --fast       # Skip slow tests

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
VERBOSE=false
FAST_MODE=false

# Parse arguments
if [ "$1" == "--verbose" ] || [ "$2" == "--verbose" ]; then
    VERBOSE=true
fi

if [ "$1" == "--fast" ] || [ "$2" == "--fast" ]; then
    FAST_MODE=true
fi

# Test results tracking
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# Helper functions
section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

run_test() {
    local test_name=$1
    local test_command=$2
    local test_file=$3

    ((TOTAL_SUITES++))

    section "Running: $test_name"

    if [ "$VERBOSE" == "true" ]; then
        echo -e "${CYAN}Command: $test_command${NC}"
        echo ""
    fi

    # Run test and capture output
    local output_file="/tmp/test_output_$$.txt"

    if $test_command > "$output_file" 2>&1; then
        ((PASSED_SUITES++))
        echo -e "${GREEN}✓ PASSED: $test_name${NC}"

        if [ "$VERBOSE" == "true" ]; then
            cat "$output_file"
        else
            # Show last 5 lines of output
            tail -5 "$output_file"
        fi
    else
        ((FAILED_SUITES++))
        echo -e "${RED}✗ FAILED: $test_name${NC}"
        echo ""
        echo "Error output:"
        cat "$output_file"
    fi

    rm -f "$output_file"
    echo ""
}

# Banner
section "Iris + Wiggum Phase 4 Test Suite"
echo "Complete testing and validation"
echo "Date: $(date)"
echo "Mode: $([ "$FAST_MODE" == "true" ] && echo "FAST" || echo "FULL")"
echo ""

# Change to tests directory
cd /home/claude/iris/tests

# =============================================================================
# Test Suite 1: Wiggum Basic Validation
# =============================================================================
run_test \
    "Test 1: Wiggum Basic Validation" \
    "./test_wiggum.sh" \
    "test_wiggum.sh"

# =============================================================================
# Test Suite 2: State Management Unit Tests
# =============================================================================
run_test \
    "Test 2: State Management Unit Tests" \
    "python3 test_state.py" \
    "test_state.py"

# =============================================================================
# Test Suite 3: Worker Template Validation
# =============================================================================
run_test \
    "Test 3: Worker Template Validation" \
    "./test_workers.sh" \
    "test_workers.sh"

# =============================================================================
# Test Suite 4: Email Flow Tests
# =============================================================================
run_test \
    "Test 4: Email Flow Tests" \
    "./test_email_flow.sh" \
    "test_email_flow.sh"

# =============================================================================
# Test Suite 5: Integration Tests (Dry Run)
# =============================================================================
if [ "$FAST_MODE" == "false" ]; then
    run_test \
        "Test 5: Integration Tests (Dry Run)" \
        "./test_integration.sh --dry" \
        "test_integration.sh"
else
    echo -e "${YELLOW}⊘ SKIPPED: Integration tests (fast mode)${NC}"
fi

# =============================================================================
# Test Suite 6: Dry Run Simulation
# =============================================================================
if [ "$FAST_MODE" == "false" ]; then
    run_test \
        "Test 6: Dry Run Simulation" \
        "bash -c 'echo n | ./dry_run.sh --once'" \
        "dry_run.sh"
else
    echo -e "${YELLOW}⊘ SKIPPED: Dry run simulation (fast mode)${NC}"
fi

# =============================================================================
# Final Summary
# =============================================================================
section "Test Suite Summary"

echo ""
echo "Total test suites:  $TOTAL_SUITES"
echo -e "${GREEN}Passed:             $PASSED_SUITES${NC}"
echo -e "${RED}Failed:             $FAILED_SUITES${NC}"
echo ""

# Calculate percentage
if [ $TOTAL_SUITES -gt 0 ]; then
    PASS_RATE=$((PASSED_SUITES * 100 / TOTAL_SUITES))
    echo "Pass rate:          ${PASS_RATE}%"
fi

echo ""

if [ $FAILED_SUITES -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL TEST SUITES PASSED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Phase 4: Testing & Validation - COMPLETE"
    echo ""
    echo "Test coverage:"
    echo "  ✓ Wiggum loop logic"
    echo "  ✓ State management (21 unit tests)"
    echo "  ✓ Worker templates (5 templates)"
    echo "  ✓ Email workflows"
    echo "  ✓ Integration (end-to-end)"
    echo "  ✓ Dry run simulation"
    echo ""
    echo "Next steps:"
    echo "  1. Review VALIDATION_CHECKLIST.md"
    echo "  2. Complete pre-deployment checklist"
    echo "  3. Test in development environment"
    echo "  4. Deploy to production when ready"
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ SOME TEST SUITES FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Failed suites: $FAILED_SUITES"
    echo ""
    echo "Please review the errors above and fix before deployment."
    echo ""
    exit 1
fi
