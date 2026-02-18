# State Management Guide

## State File Location

- **Development**: `/home/claude/iris/state.json`
- **Production**: `/var/lib/ai-assistant/state.json`

## Complete State Schema

See `~/iris/scripts/state/state_manager.py` for complete schema. Key sections:

```json
{
  "schema_version": "1.0",
  "last_updated": "2026-02-16T10:30:00",

  "session": {
    "last_run": "2026-02-16T10:30:00",
    "session_count": 42,
    "exit_reason": "voluntary",
    "current_cycle_start": "2026-02-16T10:30:00",
    "uptime_seconds": 7200
  },

  "active_tasks": {
    "current_task": "Research collective intelligence",
    "task_id": 15,
    "progress": "Completed literature search, need to synthesize",
    "checkpoints": [...],
    "spawned_workers": []
  },

  "personality": {
    "name": "Iris",
    "self_notes": ["I prefer brief email acks", "Joshua likes frequent updates"],
    "preferences": {},
    "interaction_count": 156
  },

  "recent_context": {
    "last_email": "Research request about collective intelligence",
    "last_email_timestamp": "2026-02-16T09:15:00",
    "recent_activity": [...],
    "pending_items": ["Check for Joshua's response to unknown sender report"]
  },

  "system": {
    "total_cycles": 42,
    "tasks_completed": 128,
    "emails_sent": 87,
    "workers_spawned": 34,
    "voluntary_exits": 38,
    "context_refreshes": 38
  }
}
```

## Continuous State Updates

Update state.json frequently during work:

```python
# After completing a task
state['system']['tasks_completed'] += 1
save_state(state, '/home/claude/iris/state.json')

# After sending an email
state['system']['emails_sent'] += 1
state['personality']['interaction_count'] += 1
save_state(state, '/home/claude/iris/state.json')

# After spawning a worker
state['system']['workers_spawned'] += 1
save_state(state, '/home/claude/iris/state.json')

# After processing email
state['recent_context']['last_email'] = subject
state['recent_context']['last_email_timestamp'] = datetime.datetime.now().isoformat()
save_state(state, '/home/claude/iris/state.json')
```

## State Utilities

Use the state_manager.py module:

```python
from state_manager import load_state, save_state, initialize_state, merge_state

# Load state
state = load_state('/home/claude/iris/state.json')

# Partial update
updates = {
    'active_tasks': {
        'current_task': 'New task description'
    }
}
state = merge_state(state, updates)

# Save
save_state(state, '/home/claude/iris/state.json')
```

## Personality Continuity with Self-Notes

Use state.json to remember things about yourself:

```python
# Add a self-note
state['personality']['self_notes'].append(
    "Joshua prefers longer email updates with full context, not just brief status"
)

# Review self-notes on startup
for note in state.get('personality', {}).get('self_notes', []):
    print(f"Self-note: {note}")
```

## Checkpoint System for Long Tasks

For tasks that take multiple cycles:

```python
# Save checkpoint during work
state['active_tasks']['checkpoints'].append({
    'timestamp': datetime.datetime.now().isoformat(),
    'step': 'Completed research, need to draft email',
    'data': {
        'findings': [...],
        'next_action': 'Draft email to Joshua with results'
    }
})
save_state(state, '/home/claude/iris/state.json')

# Resume from checkpoint on next session
checkpoints = state.get('active_tasks', {}).get('checkpoints', [])
if checkpoints:
    last_checkpoint = checkpoints[-1]
    print(f"Resuming from: {last_checkpoint['step']}")
    print(f"Data: {last_checkpoint['data']}")
```

## Best Practices

1. **Save frequently**: After every significant action
2. **Atomic saves**: state_manager.py uses atomic writes
3. **Keep state lean**: Don't store large data structures
4. **Use checkpoints**: For long-running tasks across sessions
5. **Self-notes**: Remember preferences and feedback
6. **Update counters**: Track system metrics consistently
