# Error Handling and Recovery

## If State is Corrupted or Missing

```python
state = load_state('/home/claude/iris/state.json')

if not state:
    print("WARNING: No state found - initializing fresh state")
    print("This may be first run, or state.json was lost/corrupted")

    # Check database for context
    recent_activity = get_recent_activity(limit=5)
    pending_tasks = list_tasks(status='pending')

    # Initialize fresh state
    state = initialize_state()

    # Add recovery note
    state['personality']['self_notes'].append(
        f"Recovered from missing state at {datetime.datetime.now().isoformat()}"
    )

    save_state(state, '/home/claude/iris/state.json')
```

## If Database is Unavailable

```python
try:
    tasks = list_tasks()
except Exception as e:
    print(f"ERROR: Database unavailable: {e}")
    print("Operating in degraded mode - using state.json only")

    # Email Joshua
    send_email(
        to='owner@example.com',
        subject='Iris: Database unavailable',
        body=f'Database connection failed: {e}\n\nOperating in degraded mode with state.json only.'
    )
```

## If Email System is Down

```python
try:
    emails = check_new_emails()
except Exception as e:
    print(f"ERROR: Email system unavailable: {e}")

    # Log to state
    state['recent_context']['pending_items'].append(
        f"Email system was down at {datetime.datetime.now().isoformat()}: {e}"
    )
    save_state(state, '/home/claude/iris/state.json')

    # Wait and retry
    time.sleep(60)
```

## Worker Failure Handling

```python
if worker.failed():
    error = worker.get_error()

    # Log failure
    log_activity(
        category='error',
        summary=f'Worker failed: {task_title}',
        details=error,
        task_id=task_id
    )

    # Update task
    update_task(task_id, status='failed', result=f'Worker error: {error}')

    # Notify Joshua
    send_email(
        to='owner@example.com',
        subject=f'Task failed: {task_title}',
        body=f'Worker subagent encountered an error:\n\n{error}\n\nI may need assistance.'
    )
```

## General Error Handling Strategy

1. **Catch and log**: Never let errors crash the controller silently
2. **Notify Joshua**: Email for any significant failures
3. **Degrade gracefully**: Continue with reduced functionality if possible
4. **State preservation**: Always save state before attempting recovery
5. **Document in logs**: Write to both database and master_log.md

## Recovery from Context Pollution

If you realize your context is heavily polluted mid-task:

```python
# Save checkpoint immediately
state['active_tasks']['progress'] = "Context polluted at step X, need to delegate remainder"
save_state(state, '/home/claude/iris/state.json')

# Spawn worker to complete the task
worker = Task(
    description="Complete task after context refresh",
    prompt=f"""Task: {task_description}

Progress so far: {state['active_tasks']['progress']}

Continue and complete from here.
"""
)

# Either wait for worker or trigger voluntary exit
```
