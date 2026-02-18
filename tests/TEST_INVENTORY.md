# Iris + Wiggum Test Inventory

Complete listing of all Phase 4 testing utilities.

**Total:** 8 test files, ~2,300 lines, ~156 tests

---

## Test Files

### 1. test_wiggum.sh
**Size:** 245 lines
**Purpose:** Basic wiggum loop validation
**Tests:** 15+
**Runtime:** ~5 seconds
**Usage:** `./test_wiggum.sh`

**Coverage:**
- File permissions
- Bash syntax
- Main loop logic
- Tmux session checks
- Service file validation
- Prompt file existence
- Claude Code availability

---

### 2. test_state.py
**Size:** 451 lines
**Purpose:** State management unit tests
**Tests:** 21 unit tests
**Runtime:** ~0.15 seconds
**Usage:** `python3 test_state.py`

**Test Classes:**
- Basic operations (4 tests)
- Atomic writes (3 tests)
- Crash resilience (3 tests)
- Schema validation (3 tests)
- Merge operations (3 tests)
- Real-world scenarios (3 tests)
- Edge cases (3 tests)

---

### 3. test_workers.sh
**Size:** 407 lines
**Purpose:** Worker template validation
**Tests:** 40+
**Runtime:** ~3 seconds
**Usage:** `./test_workers.sh`

**Coverage:**
- File existence (5 templates)
- Markdown syntax
- Required sections
- Worker-specific content
- File references
- Template consistency
- Size validation

---

### 4. test_email_flow.sh
**Size:** 475 lines
**Purpose:** Email workflow validation
**Tests:** 30+
**Runtime:** ~5 seconds
**Usage:** `./test_email_flow.sh`

**Coverage:**
- Authority validation
- Unknown sender protocol
- Authorized sender workflow
- Promise tracking
- Email watchdog
- Response timing
- Multi-step interactions

---

### 5. test_integration.sh
**Size:** 594 lines
**Purpose:** End-to-end integration tests
**Tests:** 50+
**Runtime:** ~10 seconds
**Usage:** `./test_integration.sh --dry`

**Coverage:**
- File structure
- State persistence
- Database operations
- Worker templates
- Email protocols
- Voluntary exit logic
- Full lifecycle simulation

---

### 6. dry_run.sh
**Size:** 377 lines
**Purpose:** Safe dry run mode
**Tests:** 15+ validation tests
**Runtime:** Configurable (default 60s)
**Usage:** `./dry_run.sh --once`

**Modes:**
- Single iteration: `--once`
- Timed run: `./dry_run.sh 300` (5 min)
- Default: 60 seconds

**Coverage:**
- Wiggum loop execution
- State operations
- Logging
- Resource usage
- Crash detection

---

### 7. run_all_tests.sh
**Size:** 174 lines
**Purpose:** Unified test runner
**Tests:** Runs all 6 test suites
**Runtime:** ~30 seconds (full), ~15 seconds (fast)
**Usage:** `./run_all_tests.sh`

**Modes:**
- Full: `./run_all_tests.sh`
- Verbose: `./run_all_tests.sh --verbose`
- Fast: `./run_all_tests.sh --fast`

---

### 8. VALIDATION_CHECKLIST.md
**Size:** 11KB
**Purpose:** Pre-deployment validation
**Items:** 148 checklist items
**Format:** Markdown with checkboxes

**Sections:**
- File structure (18 items)
- Configuration (15 items)
- Dependencies (8 items)
- Database (11 items)
- State management (12 items)
- Email integration (10 items)
- Test suite (8 items)
- Live testing (11 items)
- Production readiness (10 items)
- Security (9 items)
- Documentation (10 items)
- Backup & recovery (8 items)
- Performance (7 items)
- Sign-off (11 items)

---

## Quick Test Commands

### Run Individual Tests
```bash
cd /home/claude/iris/tests

# Basic validation
./test_wiggum.sh

# Unit tests
python3 test_state.py

# Worker validation
./test_workers.sh

# Email workflows
./test_email_flow.sh

# Integration (dry run)
./test_integration.sh --dry

# Dry run simulation
./dry_run.sh --once
```

### Run All Tests
```bash
cd /home/claude/iris/tests

# Full suite
./run_all_tests.sh

# With verbose output
./run_all_tests.sh --verbose

# Fast mode (skip slow tests)
./run_all_tests.sh --fast
```

---

## Test Statistics

| Metric | Count |
|--------|-------|
| Test Files | 8 |
| Total Lines | ~2,300 |
| Total Tests | ~156 |
| Unit Tests | 21 |
| Integration Tests | 50+ |
| Validation Items | 148 |
| Pass Rate | 100% |

---

## Test Coverage

**Areas Covered:**
- ✓ Wiggum loop logic
- ✓ State management (atomic writes, persistence)
- ✓ Database operations (CRUD, logging)
- ✓ Worker templates (5 templates)
- ✓ Email protocols (auth, unknown, promise)
- ✓ Voluntary exit mechanism
- ✓ Crash resilience
- ✓ Resource leak detection

**Workflows Tested:**
- ✓ Controller startup
- ✓ Email handling (authorized/unknown)
- ✓ Task lifecycle
- ✓ Worker dispatch
- ✓ State persistence across restarts
- ✓ Voluntary exit and respawn
- ✓ Promise tracking

---

## Safety

All tests are safe to run:
- No side effects on live system
- No actual controller spawns (except dry_run in test mode)
- No emails sent (simulation only)
- Automatic cleanup of temp files
- Mock operations for risky tests
- Dry run modes available

---

**Last Updated:** February 16, 2026
**Status:** All tests passing ✓
**Ready for:** Deployment validation
