"""
session_review.py - Post-session review helper for Iris.

Queries the database for recent activity, summarizes what happened,
and returns a structured dict with insights, patterns, and improvements.

Usage:
    import sys
    sys.path.append('/home/claude/iris/scripts')
    from session_review import run_session_review
    review = run_session_review(hours=4)
    # review = {
    #     'insights': [...],   # 1-3 actionable observations
    #     'patterns': [...],   # recurring behaviors noticed
    #     'improvements': [...] # concrete next-session suggestions
    # }
"""

import sys
import json
import datetime

sys.path.append('/home/claude/iris/scripts/state')


def run_session_review(hours: int = 4) -> dict:
    """
    Summarize recent activity and extract insights.

    Args:
        hours: How many hours back to look (default 4, covers one session).

    Returns:
        dict with keys: insights, patterns, improvements
        All values are lists of short strings (bullet points).
    """
    try:
        from db import get_recent_activity, list_tasks
    except ImportError as e:
        return {
            'insights': [f'Could not import db module: {e}'],
            'patterns': [],
            'improvements': ['Verify /home/claude/iris/scripts/state/db.py is accessible'],
        }

    # --- Fetch raw data ---
    try:
        activity_json = get_recent_activity(limit=50)
        activity = json.loads(activity_json) if activity_json else []
    except Exception as e:
        activity = []

    try:
        completed_json = list_tasks(status='completed')
        completed = json.loads(completed_json) if completed_json else []
        in_progress_json = list_tasks(status='in_progress')
        in_progress = json.loads(in_progress_json) if in_progress_json else []
        pending_json = list_tasks(status='pending')
        pending = json.loads(pending_json) if pending_json else []
    except Exception as e:
        completed, in_progress, pending = [], [], []

    # --- Filter to the recent window ---
    cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    cutoff_str = cutoff.strftime('%Y-%m-%dT%H:%M:%S')

    recent_activity = [
        a for a in activity
        if a.get('timestamp', '') >= cutoff_str
    ]

    # --- Count categories ---
    category_counts = {}
    error_summaries = []
    for entry in recent_activity:
        cat = entry.get('category', 'unknown')
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if cat == 'error':
            error_summaries.append(entry.get('summary', ''))

    # --- Build insights ---
    insights = []

    # Emails handled
    email_count = category_counts.get('email', 0)
    if email_count > 0:
        insights.append(f'Handled {email_count} email event(s) this session')

    # Tasks completed recently (rough: look at completed list timestamps)
    session_completed = [
        t for t in completed
        if t.get('updated_at', '') >= cutoff_str
    ]
    if session_completed:
        titles = ', '.join(t.get('title', 'untitled') for t in session_completed[:3])
        insights.append(f'Completed {len(session_completed)} task(s): {titles}')

    # Errors
    if error_summaries:
        insights.append(f'Encountered {len(error_summaries)} error(s): {"; ".join(error_summaries[:2])}')

    # Hobby / improvement activity
    improvement_count = category_counts.get('improvement', 0)
    if improvement_count > 0:
        insights.append(f'Logged {improvement_count} self-improvement event(s)')

    # Default if nothing notable
    if not insights:
        total = len(recent_activity)
        insights.append(f'Quiet session: {total} logged event(s), no major issues')

    # Cap at 3 insights
    insights = insights[:3]

    # --- Build patterns ---
    patterns = []
    if in_progress:
        patterns.append(f'{len(in_progress)} task(s) still in-progress at exit — checkpoint or hand off')
    if category_counts.get('error', 0) > 2:
        patterns.append('Multiple errors in one session — consider reviewing error-recovery.md')
    if category_counts.get('session', 0) > 10:
        patterns.append('Many session events — possible restart loop, verify watchdog stability')
    if not patterns:
        patterns.append('No notable negative patterns detected')

    # --- Build improvements ---
    improvements = []
    if pending:
        top_pending = pending[0].get('title', 'unknown') if pending else 'none'
        improvements.append(f'Next session: pick up pending task "{top_pending}" first')
    if error_summaries:
        improvements.append('Review recent errors in activity log before next complex task')
    if not improvements:
        improvements.append('Continue current approach — session went smoothly')

    return {
        'insights': insights,
        'patterns': patterns,
        'improvements': improvements,
    }


def write_session_log(review: dict, log_path: str = '/home/claude/iris/logs/session_log.md') -> None:
    """
    Append a review entry to the session log file.

    Creates the log file and its parent directory if they don't exist.
    """
    import os
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = [
        f'\n## Session Review — {timestamp}\n',
        '### Insights\n',
    ]
    for item in review.get('insights', []):
        lines.append(f'- {item}\n')
    lines.append('\n### Patterns\n')
    for item in review.get('patterns', []):
        lines.append(f'- {item}\n')
    lines.append('\n### Improvements for Next Session\n')
    for item in review.get('improvements', []):
        lines.append(f'- {item}\n')
    lines.append('\n---\n')

    with open(log_path, 'a') as f:
        f.writelines(lines)


if __name__ == '__main__':
    review = run_session_review(hours=4)
    print(json.dumps(review, indent=2))
