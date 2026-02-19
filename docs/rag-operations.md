# RAG Working Memory — Operations Guide

Iris's RAG (Retrieval-Augmented Generation) system indexes her filesystem into
a local chromadb vector store and retrieves semantically relevant context at
query time. This lets her "remember" procedures, notes, past emails, and
architecture decisions without stuffing the entire knowledge base into every
prompt.

---

## Performance Characteristics

| Metric          | Value              |
|-----------------|--------------------|
| Cold start      | ~72s (torch model load) |
| Warm query      | ~80ms              |
| Total chunks    | 2,173              |
| Source files    | 545                |
| DB size         | ~26MB              |
| DB location     | `/home/claude/iris/rag/chroma_db/` |
| Index state     | `/home/claude/iris/rag/index_state.json` |
| Embedding model | `all-MiniLM-L6-v2` (local, ~90MB) |

---

## Running Index Operations

All commands use the venv Python. Run from any directory — all paths are absolute.

### Full re-index (rebuild everything)

```bash
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/indexer.py --full
```

Use this after major changes to prompts, docs, or memory files. Takes a few
minutes. Safe to run while Iris is active (chromadb upserts are atomic).

### Incremental update (changed files only)

```bash
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/indexer.py --update
```

Compares file hashes against `/home/claude/iris/rag/index_state.json`.
Only re-indexes files that have changed. Fast — typically seconds.

Recommended cron schedule (nightly incremental):
```
0 3 * * * /home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/indexer.py --update >> /home/claude/iris/logs/rag-index.log 2>&1
```

---

## Querying Working Memory

### CLI query (ad-hoc testing)

```bash
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/query.py "how to handle unknown senders"
```

Options:
```
--n N              Number of results (default: 5)
--min-relevance F  Minimum score 0.0-1.0 (default: 0.2)
--max-chars N      Max output characters (default: 3000)
--doc-type TYPE    Filter by type (repeatable): prompt, email, note, etc.
```

### Via indexer --query flag

```bash
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/indexer.py --query "how to handle unknown senders"
```

Same output, slightly simpler invocation.

---

## Warmup (Eliminating Cold Start)

The sentence-transformers model takes ~72s to load from disk on first use.
After that, queries run in ~80ms. To pre-load before the first real email arrives:

```bash
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/warmup.py
```

Prints `RAG warmup complete. Model ready.` when done.

### Adding warmup to Iris startup (wiggum.sh)

The startup sequence lives in `/home/claude/iris/wiggum.sh`. The controller is
spawned inside a `tmux new-session` call. To warm up RAG before the controller
starts, insert the warmup call in the "Controller not running" branch:

```bash
# In wiggum.sh, in the "spawning" block:
echo "$(date): Running RAG warmup..."
/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/warmup.py
echo "$(date): RAG warmup done."

# Then spawn the controller as usual:
tmux new-session -d -s iris \
    "export POSTMARK_API_TOKEN=\"$POSTMARK_API_TOKEN\" && claude \"start\" ..."
```

Note: warmup takes ~72s on cold start. If this is too slow for the watchdog,
run warmup in the background and let the first real query absorb the delay.

Alternatively, add it as a separate startup step in the iris.service or
iris-controller.service ExecStartPre directive:

```ini
# In /etc/systemd/system/iris-controller.service:
ExecStartPre=/home/claude/iris/venv/bin/python /home/claude/iris/scripts/rag/warmup.py
```

---

## Integrating get_working_memory() into Worker Prompts

Import and call `get_working_memory()` before building any worker prompt:

```python
import sys
sys.path.insert(0, '/home/claude/iris/scripts')
from rag.rag_utils import get_working_memory

# Build context from the incoming task/email
context = f"{email_subject}\n{email_body[:500]}"

# Retrieve relevant memory (returns "" if RAG unavailable)
working_mem = get_working_memory(context, n_results=4, max_chars=2500)

# Inject into prompt
prompt = f"""
{working_mem}

You are Iris. Handle this email:
...
"""
```

The `<working_memory>` block is injected near the top of the prompt, before
the task description. It never raises — returns "" on any failure.

Good places to add `get_working_memory()` calls:
- `scripts/mail/` — email handling workers, before composing replies
- Any worker that processes tasks from the queue
- The controller itself when deciding how to route/handle a new message

---

## Indexing New Files Automatically (update_memory_for_file)

After saving any new or updated file that should be retrievable, call:

```python
from rag.rag_utils import update_memory_for_file

# After saving a new email:
update_memory_for_file('/home/claude/iris/docs/emails/2026-02-18-from-joshua.txt')
# doc_type auto-detected as 'email' from path

# After saving a note:
update_memory_for_file('/home/claude/iris/memory-legacy/notes/new-procedure.md')
# doc_type auto-detected as 'note'

# Force explicit type:
update_memory_for_file('/home/claude/iris/state.json', 'state')
```

`update_memory_for_file()` returns `True` on success, `False` on failure.
It never raises exceptions — RAG failures are logged and ignored.

### State.json Auto-indexing

`state_manager.py`'s `save_state()` now automatically calls
`update_memory_for_file()` after every successful atomic save. No manual
calls needed for state updates.

---

## File Locations

| File | Purpose |
|------|---------|
| `scripts/rag/indexer.py` | Bulk indexing, CLI entry point |
| `scripts/rag/retriever.py` | `query_memory()`, `format_for_prompt()` |
| `scripts/rag/chunker.py` | 4 chunking strategies (markdown, email, JSON, etc.) |
| `scripts/rag/query.py` | Ad-hoc CLI query tool |
| `scripts/rag/warmup.py` | Model pre-load script for startup |
| `scripts/rag/rag_utils.py` | `get_working_memory()`, `update_memory_for_file()` |
| `rag/chroma_db/` | Persistent chromadb vector store |
| `rag/index_state.json` | Tracks indexed files (hash + mtime + chunk IDs) |
| `docs/rag-design.md` | Original design document |

---

## Troubleshooting

**Cold start takes 72s on first query**
Run `warmup.py` at startup — see warmup section above.

**Query returns no results**
- Check `collection.count()` — run the indexer if DB is empty
- Lower `--min-relevance` threshold (try 0.1)
- Rephrase query to match indexed content more closely

**Index out of date**
Run `--update` to catch recent file changes. Run `--full` to rebuild from scratch.

**"No module named rag"**
Ensure `/home/claude/iris/scripts` is on `sys.path` before importing. All RAG
scripts handle this automatically via `_SCRIPTS_DIR` insertion.

**torch daemon threads hang on exit**
Always use `os._exit(0)` (not `sys.exit()`) in scripts that import torch.
All provided scripts do this.
