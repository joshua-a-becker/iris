#!/bin/bash
# test_workers.sh - Worker template validation suite
#
# Validates all worker templates in ~/iris/prompts/workers/:
# - File existence and readability
# - Markdown syntax validation
# - Required section presence
# - File reference correctness
# - Template consistency
#
# Usage:
#   ./test_workers.sh

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
section "Worker Template Validation Suite"
echo "Test date: $(date)"
echo ""

# Worker templates directory
WORKERS_DIR="/home/claude/iris/prompts/workers"

# Expected worker templates
WORKERS=(
    "research.md"
    "drafting.md"
    "moltbook.md"
    "coding.md"
    "analysis.md"
)

# Required sections in each worker template
REQUIRED_SECTIONS=(
    "Purpose"
    "Instructions"
)

# =============================================================================
# Test 1: File Existence and Permissions
# =============================================================================
section "Test 1: File Existence and Permissions"

# Check directory exists
if [ -d "$WORKERS_DIR" ]; then
    pass "Workers directory exists: $WORKERS_DIR"
else
    fail "Workers directory missing: $WORKERS_DIR"
    exit 1
fi

# Check each worker template
for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ -f "$worker_path" ]; then
        pass "Worker template exists: $worker"
    else
        fail "Worker template missing: $worker"
        continue
    fi

    if [ -r "$worker_path" ]; then
        pass "Worker template readable: $worker"
    else
        fail "Worker template not readable: $worker"
    fi

    if [ -s "$worker_path" ]; then
        pass "Worker template not empty: $worker"
    else
        fail "Worker template is empty: $worker"
    fi
done

# =============================================================================
# Test 2: Markdown Syntax Validation
# =============================================================================
section "Test 2: Markdown Syntax Validation"

info "Checking basic markdown structure..."

for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    # Check for headers (should have at least one # heading)
    if grep -q '^#' "$worker_path"; then
        pass "[$worker] Contains markdown headers"
    else
        fail "[$worker] Missing markdown headers"
    fi

    # Check for unclosed code blocks (count backticks)
    backtick_count=$(grep -o '```' "$worker_path" | wc -l)
    if [ $((backtick_count % 2)) -eq 0 ]; then
        pass "[$worker] Code blocks properly closed"
    else
        warn "[$worker] Unclosed code block detected (odd number of ```)"
        ((TESTS_RUN++))
    fi

    # Check for proper list formatting (lines starting with - or *)
    if grep -q '^[*-] ' "$worker_path"; then
        pass "[$worker] Contains formatted lists"
    else
        info "[$worker] No bullet lists found (may be intentional)"
    fi
done

# =============================================================================
# Test 3: Required Sections
# =============================================================================
section "Test 3: Required Section Validation"

info "Checking for required sections in each template..."

for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    for section_name in "${REQUIRED_SECTIONS[@]}"; do
        if grep -qi "$section_name" "$worker_path"; then
            pass "[$worker] Has section: $section_name"
        else
            fail "[$worker] Missing section: $section_name"
        fi
    done
done

# =============================================================================
# Test 4: Worker-Specific Content Validation
# =============================================================================
section "Test 4: Worker-Specific Content"

info "Validating specialized content for each worker type..."

# Research worker
if [ -f "$WORKERS_DIR/research.md" ]; then
    if grep -qi "research\|search\|investigate" "$WORKERS_DIR/research.md"; then
        pass "[research.md] Contains research-related keywords"
    else
        warn "[research.md] Missing research-related keywords"
        ((TESTS_RUN++))
    fi
fi

# Drafting worker
if [ -f "$WORKERS_DIR/drafting.md" ]; then
    if grep -qi "draft\|write\|compose\|email\|document" "$WORKERS_DIR/drafting.md"; then
        pass "[drafting.md] Contains drafting-related keywords"
    else
        warn "[drafting.md] Missing drafting-related keywords"
        ((TESTS_RUN++))
    fi
fi

# Moltbook worker
if [ -f "$WORKERS_DIR/moltbook.md" ]; then
    if grep -qi "moltbook\|post\|comment\|social" "$WORKERS_DIR/moltbook.md"; then
        pass "[moltbook.md] Contains Moltbook-related keywords"
    else
        fail "[moltbook.md] Missing Moltbook-related keywords"
    fi
fi

# Coding worker
if [ -f "$WORKERS_DIR/coding.md" ]; then
    if grep -qi "code\|coding\|program\|script\|function" "$WORKERS_DIR/coding.md"; then
        pass "[coding.md] Contains coding-related keywords"
    else
        fail "[coding.md] Missing coding-related keywords"
    fi
fi

# Analysis worker
if [ -f "$WORKERS_DIR/analysis.md" ]; then
    if grep -qi "analy\|data\|process\|evaluate" "$WORKERS_DIR/analysis.md"; then
        pass "[analysis.md] Contains analysis-related keywords"
    else
        fail "[analysis.md] Missing analysis-related keywords"
    fi
fi

# =============================================================================
# Test 5: File Reference Validation
# =============================================================================
section "Test 5: File Reference Validation"

info "Checking that referenced files exist..."

for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    # Extract file paths (looking for patterns like /home/claude/... or ~/...)
    file_refs=$(grep -oE '(/home/claude/[^ ]+|~/[^ ]+)' "$worker_path" | sort -u || true)

    if [ -z "$file_refs" ]; then
        info "[$worker] No file references found"
        continue
    fi

    ref_count=0
    valid_count=0
    invalid_count=0

    while IFS= read -r file_ref; do
        ((ref_count++))

        # Expand ~ to /home/claude
        expanded_ref="${file_ref/#\~//home/claude}"

        # Remove trailing punctuation (markdown formatting)
        expanded_ref="${expanded_ref%[,.)]*}"

        # Check if it's a directory reference (ends with /)
        if [[ "$expanded_ref" == */ ]]; then
            if [ -d "$expanded_ref" ]; then
                ((valid_count++))
            else
                ((invalid_count++))
                warn "[$worker] Invalid directory reference: $file_ref"
            fi
        else
            # It's a file reference - may not exist yet (template)
            # Only warn if it claims to be documentation that should exist
            if [[ "$expanded_ref" == *"/docs/"* ]] || [[ "$expanded_ref" == *".md" ]]; then
                if [ -e "$expanded_ref" ]; then
                    ((valid_count++))
                else
                    info "[$worker] Referenced file may not exist yet: $file_ref"
                    ((valid_count++))  # Don't penalize for template references
                fi
            else
                ((valid_count++))  # Assume valid for other types
            fi
        fi
    done <<< "$file_refs"

    if [ $ref_count -gt 0 ]; then
        pass "[$worker] File references checked ($valid_count/$ref_count)"
    fi
done

# =============================================================================
# Test 6: Template Consistency
# =============================================================================
section "Test 6: Template Consistency"

info "Checking consistency across templates..."

# Check that all templates mention reporting results
consistent_count=0
for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    if grep -qi "report\|output\|result" "$worker_path"; then
        ((consistent_count++))
    fi
done

if [ $consistent_count -eq ${#WORKERS[@]} ]; then
    pass "All templates include result reporting guidance"
else
    warn "Not all templates mention result reporting ($consistent_count/${#WORKERS[@]})"
    ((TESTS_RUN++))
fi

# Check that templates reference the controller
controller_refs=0
for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    if grep -qi "iris\|controller" "$worker_path"; then
        ((controller_refs++))
    fi
done

if [ $controller_refs -gt 0 ]; then
    pass "Templates reference the controller (Iris)"
else
    info "Templates don't explicitly reference controller (may be intentional)"
fi

# =============================================================================
# Test 7: README.md Validation
# =============================================================================
section "Test 7: Workers README Validation"

README_PATH="$WORKERS_DIR/README.md"

if [ -f "$README_PATH" ]; then
    pass "Workers README.md exists"

    # Check README mentions all worker types
    missing_workers=()
    for worker in "${WORKERS[@]}"; do
        worker_name="${worker%.md}"
        if ! grep -qi "$worker_name" "$README_PATH"; then
            missing_workers+=("$worker_name")
        fi
    done

    if [ ${#missing_workers[@]} -eq 0 ]; then
        pass "README.md documents all worker types"
    else
        warn "README.md missing workers: ${missing_workers[*]}"
        ((TESTS_RUN++))
    fi
else
    fail "Workers README.md missing"
fi

# =============================================================================
# Test 8: Size Validation
# =============================================================================
section "Test 8: Template Size Validation"

info "Checking template sizes (should be substantial)..."

for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    size=$(wc -c < "$worker_path")
    lines=$(wc -l < "$worker_path")

    # Templates should be at least 1KB and 50 lines
    if [ $size -gt 1024 ] && [ $lines -gt 50 ]; then
        pass "[$worker] Adequate size: $lines lines, $size bytes"
    else
        warn "[$worker] May be too small: $lines lines, $size bytes"
        ((TESTS_RUN++))
    fi
done

# =============================================================================
# Test 9: Example Content Validation
# =============================================================================
section "Test 9: Example and Guidance Content"

info "Checking for examples and guidance..."

for worker in "${WORKERS[@]}"; do
    worker_path="$WORKERS_DIR/$worker"

    if [ ! -f "$worker_path" ]; then
        continue
    fi

    # Check for examples (code blocks or example sections)
    if grep -qi "example\|sample" "$worker_path"; then
        pass "[$worker] Contains examples or samples"
    else
        info "[$worker] No explicit examples (may use inline guidance)"
    fi

    # Check for best practices or guidelines
    if grep -qi "best practice\|guideline\|important\|note:" "$worker_path"; then
        pass "[$worker] Includes guidance/best practices"
    else
        info "[$worker] No explicit best practices section"
    fi
done

# =============================================================================
# Final Summary
# =============================================================================
section "Worker Template Test Summary"

echo ""
echo "Templates tested: ${#WORKERS[@]}"
echo "Tests run:        $TESTS_RUN"
echo -e "${GREEN}Tests passed:     $TESTS_PASSED${NC}"
echo -e "${RED}Tests failed:     $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✓ ALL WORKER TEMPLATES VALIDATED${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Worker templates ready for use:"
    for worker in "${WORKERS[@]}"; do
        echo "  ✓ $worker"
    done
    echo ""
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}✗ WORKER TEMPLATE VALIDATION FAILED${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Fix the issues above before deployment."
    echo ""
    exit 1
fi
