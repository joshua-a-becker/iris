# RAG Working Memory System — Design Document

**Status:** Design complete, skeleton written. Full implementation in chunk 2.
**Date:** 2026-02-18
**Author:** Iris (worker agent, chunk 1)

---

## 1. Purpose

At task/email arrival time, retrieve the K most semantically relevant chunks from
Iris's filesystem and inject them into the worker prompt as "contextual working
memory." This gives workers background knowledge about past conversations, Joshua's
preferences, Iris's procedures, and ongoing context — without stuffing the entire
filesystem into every prompt.

---

## 2. Filesystem Survey

### What exists to be indexed

| Path | Content type | Files | Size | Update freq |
|------|-------------|-------|------|-------------|
| `iris/prompts/` | System prompts, worker guides, anti-patterns | ~12 .md | 156 KB | Rare (days/weeks) |
| `iris/prompts/docs/` | Email etiquette, state management, error recovery | 5 .md | ~60 KB | Rare |
| `iris/prompts/workers/` | Per-worker system prompts | 7 .md | ~60 KB | Rare |
| `iris/explorations/` | Hobby/intellectual explorations | ~17 .md | 584 KB | Daily |
| `iris/docs/architecture.md` | System architecture doc | 1 .md | — | Rare |
| `iris/docs/operations/` | Email loop, restructure plan, subagent learning | 3 .md | — | Occasional |
| `iris/docs/services/` | DigitalOcean, Moltbook, mail server docs | 3 .md | — | Rare |
| `iris/memory-legacy/notes/` | Joshua preferences, revenue ideas, system quirks | 6 .md | 140 KB | Occasional |
| `iris/memory-legacy/procedures/` | Email handling, Moltbook ops, subagent patterns | 3 .md | 40 KB | Occasional |
| `iris/logs/session_log.md` | Session-level narrative log | 1 .md | ~76 KB | Each session |
| `iris/logs/hobby_*.md` | Per-hobby session logs | ~3 .md | — | Daily |
| `iris/creative/` | Short fiction, creative writing | 1 .md | — | Occasional |
| `iris/writing/` | Flash fiction | 1 .md | — | Occasional |
| `iris/state.json` | Live Iris state (hobbies, tasks, personality) | 1 .json | ~65 KB | Every cycle |
| `iris/docs/emails/` | Archived email threads (plain text) | ~494 .txt | 5.0 MB | Daily |
| `iris/DESIGN_NOTES.md` | High-level design notes | 1 .md | — | Occasional |
| `iris/OPERATIONS_MANUAL.md` | Operations manual | 1 .md | — | Rare |

**Total corpus estimate:**
- High-value docs (prompts, notes, procedures, explorations): ~150 files, ~1.1 MB
- Email archive: ~494 files, 5.0 MB
- **Realistic indexing target:** ~700 chunks after chunking high-value docs + recent emails

### Files deliberately excluded

- `iris/docs/emails/` older than 30 days — low retrieval value, adds noise
- `.git/` objects — binary, irrelevant
- `*.pyc`, `*.db` — binary
- `iris/venv/` — third-party library code, not Iris's knowledge

---

## 3. Embedding Method

### Chosen: sentence-transformers `all-MiniLM-L6-v2` (Option A — local)

**Reasoning:**

| Factor | Local (all-MiniLM-L6-v2) | Anthropic API | Decision |
|--------|-------------------------|---------------|----------|
| Cost per query | $0 | ~$0.00001/1K tokens | Local wins |
| Latency | ~50-200ms after load | ~200-500ms + network | Local wins |
| RAM | ~100MB loaded | 0 (API call) | API marginal win |
| Offline | Yes | No | Local wins |
| Quality | Good (384-dim) | Higher | API marginal win |
| ANTHROPIC_API_KEY | Not set | Required | Local wins |

The ANTHROPIC_API_KEY is not set in the environment, which removes the API option
without configuration changes. More importantly, for a system that runs at every
email/task arrival (potentially dozens of times per day), local embeddings have zero
marginal cost and lower latency.

**RAM assessment:** The box has 3.8 GB total / ~1.7 GB currently available. The
all-MiniLM-L6-v2 model is ~90 MB on disk, ~100-150 MB loaded in RAM. This is
comfortably within budget. The model is already downloaded and verified working.

**Important runtime note:** The indexer process should call `os._exit(0)` instead of
`sys.exit()` to avoid torch daemon thread cleanup hangs. This is a known torch
behavior on CPU-only systems.

---

## 4. Vector Store

### Chosen: chromadb (persistent, Python-native)

**Reasoning:**

| Store | Install | RAM | Persistence | API simplicity | Decision |
|-------|---------|-----|-------------|----------------|----------|
| chromadb | pip, Python | Low (lazy) | Yes (SQLite) | Excellent | **CHOSEN** |
| numpy + pickle | stdlib | Very low | Manual | Simple | Fallback |
| hnswlib | pip | Low | File-based | Medium | Alternative |
| faiss-cpu | pip | Medium | File-based | Complex | Overkill |
| sqlite-vss | system dep | Low | Yes | Medium | Not available |

chromadb uses SQLite under the hood, loads collections lazily, and has a clean Python
API (add, query, update, delete). For ~700-1000 chunks, the entire vector index fits
comfortably in RAM during query time (~3 MB for 384-dim floats * 1000 vectors).

**Storage path:** `/home/claude/iris/rag/chroma_db/`

---

## 5. Chunking Strategy

### Chunk sizes by document type

| Document type | Strategy | Chunk size | Overlap |
|--------------|----------|------------|---------|
| Markdown docs (prompts, notes, procedures) | Section-based (split on `##` headings) | ~300-500 tokens | 0 (sections are self-contained) |
| Exploration logs | Split on `##` or `**Key` headers | ~400-600 tokens | 50 tokens |
| Email archives | One chunk per email (already bounded) | Whole file (~200-800 tokens) | 0 |
| state.json | Split into logical sections (hobbies, tasks, personality, recent_context) | Per top-level key | 0 |
| Session logs | Split on date/session boundaries | ~500 tokens | 0 |

**Minimum chunk size:** 50 tokens (skip metadata-only stubs)
**Maximum chunk size:** 800 tokens (split long sections mid-paragraph if needed)

### Metadata stored per chunk

```python
{
    "id": "sha256_of_path_and_content[:16]",
    "document": "chunk text",
    "metadata": {
        "path": "/home/claude/iris/prompts/docs/email-etiquette.md",
        "section": "## Reply timing",
        "doc_type": "prompt",      # prompt | note | procedure | exploration | email | state | log
        "mtime": 1708300000.0,     # file modification time (for incremental updates)
        "chunk_index": 0,          # position within file
        "file_hash": "abc123...",  # full file content hash (for change detection)
    }
}
```

---

## 6. Update Frequency

### Trigger-based incremental updates (not scheduled polling)

| Trigger | Action |
|---------|--------|
| Iris startup / session start | Run `update_index()` — incremental scan |
| New file written to `iris/explorations/` | Index that file immediately |
| New file written to `iris/logs/` | Index that file |
| New email archived to `iris/docs/emails/` | Index that email |
| `state.json` modified | Re-index state.json sections |
| Manual via CLI | `python -m iris.scripts.rag.indexer --full` |

**Full re-index:** Only needed after major restructure or if index is corrupted.
Estimated time: ~30 seconds for 700 chunks (CPU-only, batched encoding).

**Incremental update:** Compare file mtime + hash against stored metadata. Skip
unchanged files. Estimated time: ~1-5 seconds for a typical session delta.

---

## 7. Query Interface Design

### Function signature

```python
def query_memory(
    query_text: str,
    n_results: int = 5,
    doc_types: list[str] | None = None,   # filter by type
    min_relevance: float = 0.3,            # cosine distance cutoff
) -> list[MemoryChunk]:
    ...
```

### MemoryChunk structure

```python
@dataclass
class MemoryChunk:
    text: str
    path: str
    section: str
    doc_type: str
    relevance: float   # 1.0 - cosine_distance
```

### Formatted output for prompt injection

```python
def format_for_prompt(chunks: list[MemoryChunk]) -> str:
    """Returns a formatted block ready to inject into a worker prompt."""
```

Output format:
```
<working_memory>
[Source: prompts/docs/email-etiquette.md | Type: prompt | Relevance: 0.87]
Reply to all emails within the same session they arrive. For Joshua's emails,
confirm receipt immediately then do the work...

[Source: memory-legacy/notes/joshua-preferences.md | Type: note | Relevance: 0.81]
Joshua prefers concise, direct updates. Dislikes being CCed on internal details...
</working_memory>
```

---

## 8. Integration Point: Prompt Injection

### Where it gets called

In `iris-service.py` (the main controller), before spawning a worker:

```python
# Pseudo-code for integration (chunk 3/4 will implement this)
from iris.scripts.rag.retriever import query_memory, format_for_prompt

def handle_email(email):
    # Build query from email subject + first 200 chars of body
    query = f"{email.subject}: {email.body[:200]}"

    chunks = query_memory(query, n_results=5)
    memory_block = format_for_prompt(chunks)

    # Inject into worker prompt
    worker_prompt = BASE_WORKER_PROMPT + "\n\n" + memory_block
    spawn_worker(worker_prompt, email)
```

### Performance budget

- Query time target: <500ms (model already loaded as singleton)
- Memory overhead: ~150MB for loaded model (acceptable on this box)
- Model loading strategy: Load once at process start, keep in memory

### Model loading pattern (singleton)

The model is expensive to load (~2-3 seconds cold). The indexer and retriever
should share a module-level singleton:

```python
_model = None

def get_model():
    global _model
    if _model is None:
        os.environ.setdefault('CUDA_VISIBLE_DEVICES', '')
        os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model
```

---

## 9. File Layout

```
/home/claude/iris/
  scripts/
    rag/
      __init__.py          # empty
      indexer.py           # index_file(), index_directory(), update_index()
      retriever.py         # query_memory(), format_for_prompt()  [chunk 2]
      chunker.py           # text chunking logic                  [chunk 2]
  rag/
    chroma_db/             # chromadb persistent storage (auto-created)
    index_state.json       # tracks file mtimes/hashes for incremental updates
  venv/                    # Python virtual environment with chromadb + sentence-transformers
```

---

## 10. Known Constraints and Mitigations

| Constraint | Mitigation |
|-----------|------------|
| torch daemon thread hang on exit | Use `os._exit(0)` in CLI entrypoint |
| 90MB model first-download latency | Model already cached after chunk 1 test run |
| Low RAM (1.7 GB available) | Model is ~150MB; chromadb index ~5MB; safe |
| No ANTHROPIC_API_KEY | Local model is self-sufficient |
| Email archive is 5MB / 494 files | Index only recent 60 days; configurable cutoff |

---

## 11. What Chunk 2 Should Implement

1. `chunker.py` — full text chunking logic for each doc type
2. `retriever.py` — `query_memory()` and `format_for_prompt()`
3. Wire `update_index()` body in `indexer.py` (replace TODOs)
4. Test: index the actual iris filesystem, run sample queries
5. Benchmark: confirm <500ms query time, ~150MB RAM footprint
6. CLI entrypoint: `python -m iris.scripts.rag.indexer --update` and `--full`
