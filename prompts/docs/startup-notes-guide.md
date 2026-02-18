# Startup Notes Guide

## Purpose

`startup_notes` is a field in `state.json` that allows Iris to leave explicit instructions for the next startup. This ensures critical tasks and context are immediately visible when resuming after a restart.

## Location

`state.json` → `session` → `startup_notes` (array)

## Structure

Each startup note is a dictionary with:
```json
{
  "priority": "high|medium|low",
  "note": "Brief description of what needs attention",
  "action": "Specific action to take",
  "timestamp": "ISO timestamp when note was created (optional)"
}
```

## Usage Pattern

### When Exiting (Voluntary Exit)

Before exiting, add startup notes for anything that needs immediate attention on next startup:

```python
import sys
sys.path.append('/home/claude/iris/scripts/state')
from state_manager import load_state, save_state

state = load_state('/home/claude/iris/state.json')

# Add startup note
state['session']['startup_notes'].append({
    'priority': 'high',
    'note': 'Email from Joshua about urgent task',
    'action': 'Read email 8a6f1383e78e and respond immediately'
})

save_state(state, '/home/claude/iris/state.json')
```

### When Starting Up (Startup Procedure)

**STEP 1a (NEW)**: After loading state, check for startup_notes FIRST:

```python
state = load_state('/home/claude/iris/state.json')

# Check for startup notes
if state.get('session', {}).get('startup_notes'):
    print("=== STARTUP NOTES ===")
    for note in state['session']['startup_notes']:
        print(f"[{note['priority'].upper()}] {note['note']}")
        print(f"  Action: {note['action']}")

    # Process high-priority notes immediately
    high_priority = [n for n in state['session']['startup_notes']
                     if n['priority'] == 'high']

    if high_priority:
        print("\n⚠️ HIGH PRIORITY ITEMS - Handle immediately!")

    # CLEAR startup notes after reading (they're one-time)
    state['session']['startup_notes'] = []
    save_state(state, '/home/claude/iris/state.json')
```

## Common Use Cases

### 1. Urgent Email Response
```python
state['session']['startup_notes'].append({
    'priority': 'high',
    'note': 'Urgent email from Joshua needs immediate response',
    'action': 'Read email ID abc123 and respond before other tasks'
})
```

### 2. Task Resumption
```python
state['session']['startup_notes'].append({
    'priority': 'medium',
    'note': 'Research worker for task #15 completed',
    'action': 'Process results from /tmp/research_output.json and email Joshua'
})
```

### 3. System Issues
```python
state['session']['startup_notes'].append({
    'priority': 'high',
    'note': 'Email sending failed due to Postmark config',
    'action': 'Check POSTMARK_API_TOKEN and retry pending sends'
})
```

### 4. Context Reminders
```python
state['session']['startup_notes'].append({
    'priority': 'low',
    'note': 'Was exploring music theory hobby when exited',
    'action': 'Check if hobby worker completed, log results'
})
```

## Best Practices

1. **Be Specific**: Include exact actions, email IDs, file paths
2. **Use Priorities**:
   - `high` = Must do immediately (urgent emails, time-sensitive)
   - `medium` = Do before regular work (task completions, follow-ups)
   - `low` = Context reminders, nice-to-haves
3. **Clear After Reading**: Startup notes are one-time use - clear them after processing
4. **Don't Overuse**: Only use for things that truly need immediate attention
5. **Include Context**: Enough detail to understand the situation without searching

## Integration with Startup Procedure

Updated startup sequence:

```
1. Load State from state.json
2. Check and Process Startup Notes ← NEW!
   - Display all notes
   - Handle high-priority items immediately
   - Clear notes after reading
3. Restore Context (from state.json)
4. Check Database (tasks, recent activity)
5. Check Email (watchdog/polling)
6. Log Session Start
7. Spawn Watchdog
```

## Example Session

**Before exit:**
```python
state['session']['startup_notes'].append({
    'priority': 'high',
    'note': 'Tomorrow at 11am: Send reassuring emails to Shaina (surgery)',
    'action': 'Check time, if >= 11am, start task #27 immediately'
})
```

**Next startup:**
```
=== STARTUP NOTES ===
[HIGH] Tomorrow at 11am: Send reassuring emails to Shaina (surgery)
  Action: Check time, if >= 11am, start task #27 immediately

⚠️ HIGH PRIORITY ITEMS - Handle immediately!

[Processing high-priority notes...]
[Current time: 10:45am - not yet time, set reminder]
[Cleared startup notes]
```

## Notes

- Startup notes survive crashes (persisted in state.json)
- Cleared automatically after reading (prevents stale notes)
- Can be added at any time during session
- Particularly useful before voluntary exits
- Helps maintain continuity across restart cycles
