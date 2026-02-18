# Iris + Wiggum Design Notes

This file captures design decisions and clarifications that emerged during implementation.

## Watchdog Script Design (2026-02-16)

**Decision:** The email polling mechanism should be called a "watchdog" script, not just an "email monitor."

**Rationale:** While it currently monitors email at 1-second intervals, the design should be extensible. Later we can add other monitoring capabilities:
- File system changes (watch for updates to specific files)
- System status checks
- Other event sources

**Core Pattern:** The watchdog is fundamentally a sleeper agent that waits for a Python loop to break. When the monitored condition is met (email arrives, file changes, etc.), the Python loop exits, which signals the controller.

**Implementation Notes:**
- Keep 1-second polling for email (proven to work well)
- Design the watchdog to be easily extensible for additional monitoring types
- Controller spawns watchdog at startup, checks for its completion signal
- When watchdog exits (condition met), controller handles the event and restarts watchdog

**File location:** `~/iris/scripts/watchdog.py` (to be implemented in Phase 2/3)

---

*This file will be updated as design decisions are made during implementation.*

## Email Promise Tracking (2026-02-16)

**Critical Principle:** Anything promised in an email must be reflected in the queue or another data state update.

**Why:** This ensures integrity and follow-through. Promises don't get lost or forgotten across context resets.

**Implementation:** Hardcode this principle into the new controller prompt (existential-instructions.md or iris.md).

**Examples:**
- Email: "I'll research X and send you a report" → Create task in queue
- Email: "I'll monitor Y and let you know" → Update state.json with monitoring task
- Email: "I'll fix Z" → Queue the fix task

**Verification:** Before sending any email reply, check:
1. Did I promise something specific?
2. If yes, have I created a task/updated state to track it?
3. If no tracking yet, add it before sending email

**File location:** This principle should be in the core controller prompt in Phase 3.


## Resource Management and Agent Limits (2026-02-16)

**Critical Principle:** Extra cognitive agents are for urgency only.

**Context:** Today ran 2 cognitive agents in parallel (Phase 2 + email headers). Joshua cautioned: nothing was urgent, be careful about CPU resources, don't want a stroke!

**Rules to bake into new system:**

1. **Default: Single cognitive agent at a time**
   - One task, one agent
   - Serial execution by default
   - Keep it simple and resource-efficient

2. **Extra agents only for true urgency:**
   - Client waiting for immediate response
   - Time-critical deadline
   - High-priority interrupt from Joshua
   - NOT for: parallel development work, convenience, "getting things done faster"

3. **Watchdog resource monitoring:**
   - Monitor CPU usage continuously
   - Monitor swap usage continuously
   - **Break conditions (warn controller, don't interrupt):**
     - CPU >= 95%
     - Swap near-full (>80%?)
   - When watchdog breaks: controller assesses situation, decides action
   - Controller might: pause work, checkpoint and exit, kill low-priority worker

4. **Why this matters:**
   - 2-core CPU is the constraint (can't add more cores easily)
   - Multiple Claude instances compete for CPU
   - Swap usage = memory pressure = slowness
   - Better to work serially and finish reliably than thrash in parallel

**Implementation locations:**
- Controller prompt (iris.md): Emphasize single-agent default, urgency criteria
- Watchdog script: Add CPU and swap monitoring with break conditions
- State.json schema: Track resource usage, warn thresholds

**Lesson learned:** Parallel work is tempting when tasks are independent, but resource constraints matter. Trust serial execution.

