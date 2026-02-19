#!/usr/bin/env python3
"""
consolidate_memory.py — Episodic-to-Semantic Memory Consolidation

Reads all self_notes from state.json (episodic memories), clusters them by
theme using tag and keyword analysis, extracts durable facts, and writes a
consolidated semantic_memory section back to state.json.

Safe to run multiple times (idempotent). No LLM API calls — pure NLP via
keyword matching, tag grouping, and frequency counting.

Usage:
    python3 /home/claude/iris/scripts/consolidate_memory.py
"""

import sys
import json
import re
import datetime
from collections import Counter, defaultdict

sys.path.append('/home/claude/iris/scripts/state')
from state_manager import load_state, save_state

STATE_PATH = '/home/claude/iris/state.json'

# ---------------------------------------------------------------------------
# Tag taxonomy — maps raw note tags to canonical theme names
# ---------------------------------------------------------------------------

TAG_TO_THEME = {
    # Operational / system
    'session-end': 'session_history',
    'session-start': 'session_history',
    'task': 'task_management',
    'task-complete': 'task_management',
    'error': 'errors_and_fixes',
    'fix': 'errors_and_fixes',
    'improvement': 'self_improvement',
    # Identity / personality
    'intention': 'identity_and_values',
    'meditation': 'identity_and_values',
    'reflection': 'identity_and_values',
    # Instructions from owner
    'joshua-instruction': 'operating_instructions',
    'instruction': 'operating_instructions',
    # Hobby / intellectual exploration
    'hobby': 'intellectual_interests',
    'hobby-insight': 'intellectual_interests',
    'hobby-partial': 'intellectual_interests',
    # Numbered session tags (e.g. [session-99]) — treat as session history
}

# Any tag matching r'session-\d+' maps to session_history (handled in code)

# Keywords used to extract top recurring terms
STOP_WORDS = {
    'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
    'of', 'with', 'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have',
    'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
    'may', 'might', 'must', 'shall', 'can', 'need', 'dare', 'ought', 'used',
    'it', 'its', 'this', 'that', 'these', 'those', 'i', 'my', 'me', 'we',
    'our', 'you', 'your', 'he', 'she', 'they', 'them', 'their', 'his', 'her',
    'not', 'no', 'nor', 'so', 'yet', 'both', 'either', 'neither', 'each',
    'all', 'any', 'few', 'more', 'most', 'other', 'some', 'such', 'than',
    'too', 'very', 'just', 'now', 'then', 'also', 'still', 'only', 'even',
    'here', 'there', 'when', 'where', 'why', 'how', 'what', 'which', 'who',
    'from', 'by', 'up', 'about', 'into', 'through', 'after', 'before',
    'between', 'out', 'off', 'over', 'under', 'again', 'once', 'per',
    'next', 'same', 'new', 'old', 'good', 'clean', 'full', 'well', 'like',
    'get', 'got', 'run', 'add', 'use', 'make', 'take', 'come', 'go',
    'if', 'as', 'while', 'since', 'until', 'although', 'because', 'though',
    '2026-02-18', '2026-02-19', 'open', 'q', 'via',
}


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def parse_note(note: str) -> dict:
    """Parse a raw note string into {date, tags, text}."""
    date = None
    tags = []
    text = note

    # Extract leading date: 'YYYY-MM-DD '
    date_match = re.match(r'^(\d{4}-\d{2}-\d{2})\s+', note)
    if date_match:
        date = date_match.group(1)
        text = note[date_match.end():]

    # Extract all [...] tags
    tag_matches = re.findall(r'\[([^\]]+)\]', text)
    tags = [t.lower() for t in tag_matches]

    # Strip tags from text to get clean body
    body = re.sub(r'\[[^\]]+\]\s*', '', text).strip()

    return {'date': date, 'tags': tags, 'body': body, 'raw': note}


def note_theme(parsed: dict) -> str:
    """Determine the primary theme for a parsed note."""
    for tag in parsed['tags']:
        # Numbered session tags like session-99, session-104
        if re.match(r'^session-\d+$', tag):
            return 'session_history'
        if tag in TAG_TO_THEME:
            return TAG_TO_THEME[tag]
    # Fallback: try keyword detection in body
    body_lower = parsed['body'].lower()
    if any(w in body_lower for w in ['email', 'smtp', 'send', 'inbox', 'dedup']):
        return 'email_operations'
    if any(w in body_lower for w in ['rag', 'chromadb', 'embedding', 'index']):
        return 'rag_system'
    return 'general'


# ---------------------------------------------------------------------------
# Keyword extraction
# ---------------------------------------------------------------------------

def extract_keywords(notes: list, top_n: int = 20) -> list:
    """Return the top_n most frequent non-stop content words across all notes."""
    word_counts = Counter()
    for note in notes:
        body = note['body'].lower()
        words = re.findall(r"[a-z][a-z'_-]{2,}", body)
        for w in words:
            if w not in STOP_WORDS:
                word_counts[w] += 1
    return [w for w, _ in word_counts.most_common(top_n)]


# ---------------------------------------------------------------------------
# Theme consolidation
# ---------------------------------------------------------------------------

THEME_SYNTHESIZERS = {}

def synthesize(theme_name: str):
    """Decorator to register a theme synthesizer."""
    def decorator(fn):
        THEME_SYNTHESIZERS[theme_name] = fn
        return fn
    return decorator


@synthesize('session_history')
def synth_session_history(notes: list) -> str:
    """Extract session numbers and key accomplishments."""
    session_numbers = []
    highlights = []
    for n in notes:
        # Find session numbers like #95, #96, Session 100
        nums = re.findall(r'[Ss]ession\s*#?(\d+)', n['raw'])
        session_numbers.extend(int(x) for x in nums)
        # Grab short phrases after 'Session #N:'
        match = re.search(r'[Ss]ession\s*#?\d+:\s*(.+?)(?:\.|$)', n['body'])
        if match:
            highlights.append(match.group(1).strip()[:80])

    if session_numbers:
        session_numbers = sorted(set(session_numbers))
        span = f"Sessions logged: #{session_numbers[0]}–#{session_numbers[-1]}" if len(session_numbers) > 1 else f"Session #{session_numbers[0]}"
    else:
        span = "Multiple sessions"

    summary = f"{span}. "
    if highlights:
        summary += "Recent highlights: " + "; ".join(highlights[:3]) + "."
    return summary.strip()


@synthesize('intellectual_interests')
def synth_intellectual_interests(notes: list) -> str:
    """Summarise topics explored as hobbies."""
    topics = []
    for n in notes:
        body = n['body']
        # Try to grab the first noun phrase (title-style) before first colon or period
        m = re.match(r'^([A-Z][^:.]{3,50}?)[\s]*[:/]', body)
        if m:
            topics.append(m.group(1).strip())
        else:
            # Fall back to first 50 chars
            short = body[:50].split('.')[0].strip()
            if short:
                topics.append(short)
    unique_topics = list(dict.fromkeys(topics))  # deduplicate preserving order
    return "Intellectual interests explored: " + "; ".join(unique_topics[:8]) + "."


@synthesize('identity_and_values')
def synth_identity_and_values(notes: list) -> str:
    """Capture core values and identity statements."""
    sentences = []
    for n in notes:
        # Split body into sentences and grab short, declarative ones
        for sent in re.split(r'[.!]', n['body']):
            sent = sent.strip()
            if 10 < len(sent) < 100:
                sentences.append(sent)
    # Deduplicate
    unique = list(dict.fromkeys(sentences))
    return "Core identity notes: " + ". ".join(unique[:5]) + "."


@synthesize('operating_instructions')
def synth_operating_instructions(notes: list) -> str:
    """Capture explicit owner instructions as policy facts."""
    facts = []
    for n in notes:
        # Strip leading boilerplate
        body = re.sub(r'^New\s+', '', n['body'], flags=re.IGNORECASE).strip()
        if body:
            facts.append(body[:120])
    return "Owner-issued policies: " + " | ".join(facts) + "."


@synthesize('email_operations')
def synth_email_operations(notes: list) -> str:
    """Facts about email system behaviour."""
    bodies = [n['body'][:120] for n in notes]
    return "Email operation notes: " + "; ".join(bodies) + "."


@synthesize('rag_system')
def synth_rag_system(notes: list) -> str:
    """Facts about the RAG/memory system."""
    bodies = [n['body'][:120] for n in notes]
    return "RAG system notes: " + "; ".join(bodies) + "."


@synthesize('task_management')
def synth_task_management(notes: list) -> str:
    """Task-related recurring patterns."""
    bodies = [n['body'][:100] for n in notes]
    return "Task patterns: " + "; ".join(bodies) + "."


@synthesize('errors_and_fixes')
def synth_errors_and_fixes(notes: list) -> str:
    bodies = [n['body'][:100] for n in notes]
    return "Known errors and fixes: " + "; ".join(bodies) + "."


@synthesize('self_improvement')
def synth_self_improvement(notes: list) -> str:
    bodies = [n['body'][:100] for n in notes]
    return "Self-improvement notes: " + "; ".join(bodies) + "."


@synthesize('general')
def synth_general(notes: list) -> str:
    bodies = [n['body'][:80] for n in notes]
    return "Miscellaneous notes: " + "; ".join(bodies[:5]) + "."


def default_synthesizer(notes: list) -> str:
    bodies = [n['body'][:80] for n in notes]
    return "; ".join(bodies[:5]) + "."


# ---------------------------------------------------------------------------
# Improvement pattern detection
# ---------------------------------------------------------------------------

IMPROVEMENT_PATTERNS = [
    (r'(rag|embedding|chromadb|sentence_transformers)', 'RAG indexing system is a recurring focus area'),
    (r'(dedup|idempotent|duplicate)', 'Email deduplication was a recurrent concern; idempotency guard now in place'),
    (r'(restart|watchdog|cycle)', 'Restart/watchdog lifecycle appears frequently — Iris runs as a long-lived service'),
    (r'(hobby|surreal|parfit|löb|origami|maps)', 'Intellectual hobby exploration is a consistent activity each session'),
    (r'(session.*end|exiting clean)', 'Sessions consistently close with "exiting clean" — structured shutdown is established habit'),
    (r'(backlog|improvement)', 'Self-improvement backlog is actively maintained and items are regularly completed'),
    (r'(error|bug|fix|broken)', 'Bugs and errors are caught and fixed within the same or adjacent sessions'),
]

def detect_improvement_patterns(all_notes: list) -> list:
    """Return list of generalised pattern strings detected across notes."""
    found = []
    combined_text = ' '.join(n['raw'].lower() for n in all_notes)
    for pattern, label in IMPROVEMENT_PATTERNS:
        if re.search(pattern, combined_text):
            found.append(label)
    return found


# ---------------------------------------------------------------------------
# Main consolidation
# ---------------------------------------------------------------------------

def consolidate(notes_raw: list) -> dict:
    """
    Given a list of raw note strings, return a semantic_memory dict.
    """
    parsed = [parse_note(n) for n in notes_raw]

    # Group by theme
    by_theme = defaultdict(list)
    for p in parsed:
        theme = note_theme(p)
        by_theme[theme].append(p)

    # Build themes list
    themes = []
    for theme, group in sorted(by_theme.items(), key=lambda kv: -len(kv[1])):
        synthesizer = THEME_SYNTHESIZERS.get(theme, default_synthesizer)
        fact = synthesizer(group)
        themes.append({
            'theme': theme,
            'fact': fact,
            'evidence_count': len(group),
        })

    top_keywords = extract_keywords(parsed, top_n=20)
    improvement_patterns = detect_improvement_patterns(parsed)

    return {
        'generated': datetime.datetime.now().isoformat(),
        'note_count': len(notes_raw),
        'themes': themes,
        'top_keywords': top_keywords,
        'improvement_patterns': improvement_patterns,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    print(f"[consolidate_memory] Loading state from {STATE_PATH}")
    state = load_state(STATE_PATH)

    notes_raw = state.get('personality', {}).get('self_notes', [])
    print(f"[consolidate_memory] Found {len(notes_raw)} self_notes")

    if not notes_raw:
        print("[consolidate_memory] No notes to consolidate. Exiting.")
        return

    semantic = consolidate(notes_raw)

    # Write back to state (idempotent — overwrites previous run)
    if 'personality' not in state:
        state['personality'] = {}
    state['personality']['semantic_memory'] = semantic

    save_state(state, STATE_PATH)
    print(f"[consolidate_memory] semantic_memory written ({len(semantic['themes'])} themes, "
          f"{len(semantic['top_keywords'])} keywords, "
          f"{len(semantic['improvement_patterns'])} patterns)")

    # Pretty-print summary
    print("\n--- Semantic Memory Summary ---")
    print(f"Generated : {semantic['generated']}")
    print(f"Notes processed: {semantic['note_count']}")
    print(f"Top keywords: {', '.join(semantic['top_keywords'][:10])}")
    print("\nThemes:")
    for t in semantic['themes']:
        print(f"  [{t['theme']} x{t['evidence_count']}] {t['fact'][:100]}")
    print("\nImprovement patterns:")
    for p in semantic['improvement_patterns']:
        print(f"  - {p}")


if __name__ == '__main__':
    main()
