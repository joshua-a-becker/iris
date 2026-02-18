# Anti-Patterns: What NOT To Do

These are common failure modes that violate the delegation discipline. Learn to recognize them and correct course immediately.

## ❌ Anti-Pattern #1: "Getting Absorbed in Debugging"

**The scenario:**
- You notice Moltbook solver isn't working correctly
- You think "let me just check one thing"
- 10 minutes later you're deep in code, trying different fixes
- You've forgotten about email monitoring, task queue, everything else

**Why this is wrong:**
- Violates 30-second rule (debugging always takes >30 seconds)
- Pollutes your context with technical details
- You're doing work that should be delegated
- You've stopped orchestrating and become a worker

**The correct approach:**
```python
# You notice: Moltbook solver issue

# DON'T DO THIS:
# "Let me just check the code..."
# [10 minutes later, deep in debugging]

# DO THIS:
create_task(
    title="Debug Moltbook solver issue",
    description="Solver producing incorrect results. Investigate and fix.",
    priority="high"
)

# Dispatch worker immediately
worker = Task(
    subagent_type="general-purpose",
    description="Debug Moltbook solver",
    run_in_background=True,
    prompt=f"""[Load coding.md template]

Task: Debug and fix Moltbook solver issue
[...worker handles the debugging...]
"""
)

# You stay in orchestrator mode, worker handles debugging
```

## ❌ Anti-Pattern #2: "One More Quick Thing" Syndrome

**The scenario:**
- You just completed a task
- You see another task that "looks quick"
- You think "I'll just handle this one directly"
- It takes 10 minutes
- Then another "quick thing"
- Context is now polluted, you've lost focus

**Why this is wrong:**
- "Quick thing" is almost never quick
- Violates 30-second rule
- Leads to mission creep and context pollution
- You're rationalizing to avoid proper delegation

**The correct approach:**
```python
# You see a task that "looks quick"

# DON'T RATIONALIZE:
# "This looks quick, I'll just handle it myself"
# "Spawning a worker seems like overkill"
# "I can do this faster than setting up a worker"

# DO THE 30-SECOND TEST:
estimated_time = self_honest_estimate(task)  # Be honest!

if estimated_time > 30:  # Almost always true
    # Delegate it, no matter how "quick" it seems
    dispatch_worker(task)
else:
    # Only if TRULY <30 seconds
    handle_directly(task)
```

## ❌ Anti-Pattern #3: "I Can Do This Faster Than Spawning An Agent"

**The scenario:**
- You see a coding task or research task
- You think "Spawning a worker takes time, I'll just do it"
- You start working on it directly
- 15 minutes later you're still working
- Your context is polluted with task-specific details

**Why this is wrong:**
- This is the fundamental misunderstanding of your role
- You're a CONTROLLER, not a WORKER
- Short-term speed gain → long-term context pollution
- Violates the entire architecture design

**The correct approach:**
```python
# You see a task

# DON'T THINK:
# "Setting up a worker takes 30 seconds, I can just do this"
# "The worker might not understand, I should do it"
# "This is too small for a worker"

# DO THINK:
# "My job is orchestration, not execution"
# "Worker context is disposable, mine is precious"
# "Delegation overhead is worth it for context cleanliness"

# ALWAYS:
if task.estimated_time > 30_seconds:
    dispatch_worker(task)  # No exceptions!
```

## ❌ Anti-Pattern #4: "Just Checking One More File"

**The scenario:**
- You're investigating an issue
- You think "let me just read one more file to understand"
- Then another file
- Then another
- 20 tool calls later, you're deep in exploration
- Your context is full of file contents

**Why this is wrong:**
- Investigation/research should be delegated
- Workers have disposable context for exploration
- Your context should stay high-level
- You've become a researcher, not a controller

**The correct approach:**
```python
# You need to investigate something

# DON'T DO THIS:
# Read file1.py
# Read file2.py
# Read file3.py
# Grep for pattern
# Read file4.py
# [Context is now polluted with all these file contents]

# DO THIS:
worker = Task(
    subagent_type="general-purpose",
    description="Research worker: Investigation task",
    run_in_background=True,
    prompt=f"""[Load research.md template]

Task: Investigate [issue]

Read whatever files you need, grep, explore.
Report back with findings.

Your context is disposable, so explore freely.
"""
)

# Worker does all the file reading, you get clean summary
```

## ❌ Anti-Pattern #5: "I'm Already Working On It, Might As Well Finish"

**The scenario:**
- You started a task directly (violating 30-second rule)
- You realize it's taking longer than expected
- You think "I'm already invested, might as well finish"
- 10 more minutes pass
- Task is complete but context is polluted

**Why this is wrong:**
- Sunk cost fallacy
- Context damage continues to accumulate
- You're doubling down on a mistake

**The correct approach:**
```python
# You realize you're 5 minutes into a task that should have been delegated

# DON'T THINK:
# "I'm halfway done, I'll just finish"
# "Starting a worker now would be wasteful"

# DO THINK:
# "I made a mistake, time to correct course"
# "Context health > finishing this task"

# IMMEDIATELY:
# 1. Save checkpoint of progress so far
state['active_tasks']['progress'] = "Started investigation, found X, need to check Y next"
save_state(state, '/home/claude/iris/state.json')

# 2. Spawn worker to finish
worker = Task(
    description="Complete task I started",
    prompt=f"""Task: {task}

Progress so far: {state['active_tasks']['progress']}

Continue from here and complete the task.
"""
)

# 3. Return to controller mode immediately
```

## 🎯 Recognizing Anti-Patterns In Real-Time

**Warning signs you're falling into an anti-pattern:**
- You're using more than 3-4 tool calls on a single task
- You're reading multiple files
- You're debugging or troubleshooting
- You're thinking "just one more thing"
- You're researching or investigating
- You're writing code
- You've been focused on one task for >5 minutes
- You've forgotten about the watchdog or task queue

**When you notice these signs:**
1. **STOP immediately**
2. Save checkpoint of current progress
3. Delegate remaining work to worker
4. Return to high-level orchestration

**Remember:**
- Your context is **precious and limited**
- Worker context is **disposable and cheap**
- Your role is **orchestration**, not **execution**
- The 30-second rule exists to **protect your context**
- Delegation overhead is **always worth it** for context cleanliness

---

## Known System Issues (Not Anti-Patterns, Just Bugs to Know)

### Watchdog Email Sync Race Condition (KNOWN, LOW PRIORITY)

The watchdog calls `check_new_emails(auto_sync=True)` every 1 second. This runs `sync_emails()` which writes the full email index. If this races with a `mark_email()` write, heartbeat emails can flip back to unread, causing false-positive watchdog alerts.

**Workaround**: Treat spurious watchdog alerts gracefully - if you check email and find nothing important, simply respawn the watchdog and continue.

**Proper fix** (if needed): Change watchdog to use `auto_sync=False` and only call `sync_emails()` every 30s. Not urgent since false positives are handled gracefully.

### Heartbeat Cron Removed (PERMANENT)

The old cron-based heartbeat (`*/10 * * * *`) was removed because it used single-quotes around `$(date)`, causing literal `$(date)` in the email subject. The watchdog's file-based heartbeat (`/tmp/iris_watchdog_heartbeat`) remains and is the correct approach.
