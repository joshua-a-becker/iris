# Iris + Wiggum - Test Suite

**Status:** Placeholder for Phase 4

This directory will contain tests for the Iris + Wiggum architecture.

## Test Categories

### 1. Crash Recovery Tests
Test that wiggum properly respawns controller after crashes.

**Test cases:**
- Kill controller process → verify respawn within 10 seconds
- Controller crashes due to error → verify state.json preserved
- Tmux session dies → verify new session created
- Multiple rapid crashes → verify wiggum keeps trying

### 2. Voluntary Exit Tests
Test graceful context refresh mechanism.

**Test cases:**
- Trigger voluntary exit → verify state.json written
- New controller spawns → verify state loaded correctly
- Active tasks → verify resumption or clean handoff
- Personality continuity → verify "I'm Iris" persists

### 3. State Persistence Tests
Validate state.json correctness across restart cycles.

**Test cases:**
- Write state.json → restart → verify all fields intact
- Corrupt state.json → verify graceful fallback
- Missing state.json → verify fresh initialization
- Concurrent state updates → verify no race conditions

### 4. Email Handling Tests
Test email monitoring, triage, and response.

**Test cases:**
- New email arrives → verify ack sent within 30 seconds
- Authoritative sender → verify task created
- Unknown sender → verify dragon reply + forward to Joshua
- Email with attachment → verify attachment handling
- Multiple rapid emails → verify all handled

### 5. Worker Spawning Tests
Test background subagent execution.

**Test cases:**
- Spawn worker → verify Task tool used correctly
- Worker completes → verify results processed
- Worker crashes → verify controller handles gracefully
- Multiple workers → verify resource limits respected
- Long-running worker → verify controller remains responsive

### 6. Resource Management Tests
Test memory and CPU limits.

**Test cases:**
- Controller memory usage → verify stays under 500MB typical
- Worker memory usage → verify killed if > 3GB
- Disk usage → verify logs don't fill disk
- Swap usage → verify stays reasonable

### 7. Integration Tests
End-to-end system validation.

**Test cases:**
- Full cycle: email → task → worker → result → email reply
- Multi-task workflow → verify queue management
- Context refresh during active task → verify state preservation
- System reboot → verify wiggum auto-starts via systemd

## Test Utilities

//TODO: Create test helper scripts

### test_email.sh
Send test emails to claude@mail.example.com from various senders.

### test_crash.sh
Kill controller and measure respawn time.

### test_state.sh
Verify state.json schema and data integrity.

### mock_worker.py
Simulate worker subagent for testing orchestration.

## Test Database

Use separate test database to avoid polluting production:
- Test DB: /home/claude/iris/tests/test_iris.db
- Production DB: /home/claude/memory/iris.db

## Running Tests

//TODO: Create test runner

```bash
# Run all tests
cd ~/iris/tests
./run_all_tests.sh

# Run specific category
./run_tests.sh crash_recovery

# Run single test
./run_tests.sh crash_recovery test_controller_kill
```

## Continuous Testing

//TODO: Consider adding to cron for periodic validation

```bash
# Daily test run
0 2 * * * /home/claude/iris/tests/run_all_tests.sh >> /home/claude/iris/tests/test_log.txt 2>&1
```

## Test Results

Results will be logged to:
- `test_results/` - Timestamped test run outputs
- `test_log.txt` - Aggregate test history
- `failures/` - Detailed failure reports for debugging

---

**Phase 4** will populate this directory with actual test implementations.
**See STRUCTURE.md** for more details on testing strategy.
