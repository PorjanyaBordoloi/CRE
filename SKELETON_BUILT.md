# CRE v0.1 Skeleton — Build Complete ✅

## Project Structure

```
cre/
├── cre/
│   ├── __init__.py              # Package init with public API
│   ├── cli.py                   # Typer CLI with all v0.1 commands
│   ├── config.py                # Config loader/manager (.cre/config.yaml)
│   ├── vector_store.py          # L1: ChromaDB wrapper (embedding + retrieval)
│   ├── memory.py                # L2: SQLite tiered memory (3 tiers, schemas)
│   ├── sidecar.py               # L3: Pluggable LLM backends (abstract + 3 impl)
│   ├── ingestor.py              # File reading, chunking (sliding window), embedding
│   ├── retriever.py             # Orchestrates L1+L2+L3 (token-budget packing)
│   ├── injector.py              # Context formatting (markdown, plain, JSON)
│   └── tui.py                   # TUI stub (v0.2)
├── tests/
│   ├── __init__.py
│   ├── test_ingestor.py         # Tests: chunker, file ingest, directory ingest
│   ├── test_memory.py           # Tests: tiers, retrieval, stats
│   └── test_retriever.py        # Tests: L1+L2+L3 orchestration, budgeting
├── pyproject.toml               # Dependencies, build config
├── README.md                    # Getting started guide
├── CONTRIBUTING.md              # Contributing guidelines
├── .gitignore                   # Git ignore rules (.cre/ excluded)
└── SKELETON_BUILT.md            # This file
```

## What Was Built

### Core Architecture ✅

#### L1: Vector Store (ChromaDB)
- **File**: `cre/vector_store.py`
- **Features**:
  - Persistent ChromaDB with duckdb+parquet backend
  - sentence-transformers embeddings
  - Semantic search with cosine similarity
  - Chunk metadata tracking (source, domain, tier_hint, created_at)
  - Add, retrieve, delete, count, get_stats

#### L2: Tiered Memory (SQLite)
- **File**: `cre/memory.py`
- **Schema**:
  ```sql
  CREATE TABLE memory (
    id, content, tier, domain, source_file, token_count, created_at, updated_at, tags
  )
  ```
- **Features**:
  - 3 tiers: Raw (1), Summary (2), Theme (3)
  - Query by tier, domain, or combination
  - Tag support (JSON array)
  - Full CRUD + statistics
  - Indexed on tier, domain, source_file

#### L3: Sidecar Backends
- **File**: `cre/sidecar.py`
- **Abstract Base**: `SidecarBackend` with compress() + rank()
- **Implementations**:
  - `AnthropicSidecar` (Claude Haiku)
  - `OpenAISidecar` (GPT-4o-mini)
  - `OllamaSidecar` (local models)
  - `NoOpSidecar` (passthrough, no API calls)
- **Features**:
  - Token logging to `.cre/token_log.jsonl`
  - API key from environment variable
  - Rank chunks by query relevance
  - Compress/summarize text

#### Retriever (Orchestrator)
- **File**: `cre/retriever.py`
- **Core Logic**:
  1. L1 vector search (top-K)
  2. L2 tier fetch (themes + summaries for matching domains)
  3. L3 sidecar rank (optional compression)
  4. Budget-aware tier packing (greedy fill: themes → summaries → facts)
- **Returns**: `ContextBundle` with themed/summary/fact content + metadata

#### Ingestor (File Pipeline)
- **File**: `cre/ingestor.py`
- **Chunker**:
  - Sliding window chunking (configurable size + overlap)
  - Paragraph-aware splitting
  - Sentence splitting for long paragraphs
  - Token counting with tiktoken
- **Ingestor**:
  - Single file + directory ingestion
  - Recursive directory traversal
  - Auto-population of L1 (vector_store) + L2 (memory)

### CLI Commands ✅

- **`cre init [path]`** — Initialize project with config, stores
- **`cre ingest <path>`** — Ingest files/dirs into L1+L2
  - `--tier` (1-3)
  - `--domain` (research, academics, music, self, synthesis, aria)
- **`cre retrieve <query>`** — Vector search + tier fetch, display results
  - `--top-k` (default 5)
  - `--budget` (tokens, defaults to config)
- **`cre inject <query>`** — Retrieve + format for prompt injection
  - `--budget` (tokens)
  - `--format` (markdown, plain, json)
- **`cre compress <file>`** — Compress session log, file into memory
  - `--tier` (2 or 3)
- **`cre status`** — Show vector store, memory, config stats (Rich table)
- **`cre tui`** — TUI launcher (v0.2 stub with message)
- **`cre lint`** — Health checks (v0.2 stub with message)

**All commands**:
- ✅ Have `--help` strings
- ✅ Use Rich for terminal output
- ✅ Handle errors gracefully

### Configuration ✅

- **File**: `cre/config.py` + `.cre/config.yaml` template
- **Schema**:
  ```yaml
  version: '0.1'
  sidecar:
    backend: anthropic  # | openai | ollama | none
    model: claude-haiku-4-5
    api_key_env: ANTHROPIC_API_KEY
  embedding:
    model: all-MiniLM-L6-v2
    chunk_size: 512
    chunk_overlap: 64
  memory:
    default_inject_budget: 2000
    tier_weights: [0.5, 0.35, 0.15]
  ```
- **Features**:
  - Load from YAML, use defaults if missing
  - Dot-notation access (e.g., `config.get('sidecar.backend')`)
  - Save/initialize
  - Property shortcuts

### Testing (pytest stubs) ✅

**test_ingestor.py**:
- `TestChunker`: chunk sizes, token counting, short/long text
- `TestIngestor`: file/dir ingest, domain/tier support, error handling

**test_memory.py**:
- `TestMemory`: CRUD ops, tier retrieval, domain filtering, stats

**test_retriever.py**:
- `TestContextBundle`: dataclass creation
- `TestRetriever`: orchestration, budget respect, tier packing, compression

**All tests**:
- Use `pytest` fixtures
- Use `tmp_path` for isolated databases
- Cover happy paths + error cases

### Documentation ✅

- **README.md**: One-line pitch, quick start, architecture, commands, comparison table
- **CONTRIBUTING.md**: Dev setup, architecture overview, patterns for adding features, good first issues

## Key Design Decisions

1. **Abstract Base Class Pattern** (L3)
   - `SidecarBackend` ABC ensures consistent interface
   - `get_sidecar()` factory for pluggability

2. **Token Counting**
   - Using `tiktoken` for accurate token estimates
   - Tracked in memory for budget calculations

3. **Tier Weights**
   - Configurable budget allocation: [themes 50%, summaries 35%, facts 15%]
   - Greedy packing fills budget tier-by-tier

4. **Local-First**
   - All state in `.cre/` directory (gitignored)
   - SQLite + persistent ChromaDB
   - Config as human-readable YAML

5. **Error Handling**
   - User-friendly Rich console output
   - Graceful fallbacks (e.g., ranking fails → use original order)

## Dependencies

```
typer[all]>=0.12          # CLI framework
chromadb>=0.5             # L1 vector store
sentence-transformers>=3  # Embeddings
anthropic>=0.25           # L3: Anthropic
openai>=1.0               # L3: OpenAI
ollama>=0.2               # L3: Ollama
textual>=0.60             # TUI (v0.2)
rich>=13                  # Terminal output
pyyaml>=6                 # Config
tiktoken>=0.7             # Token counting
```

## Next Steps

### v0.1 Polish (if needed)
- [ ] Test edge cases (empty budgets, huge files, no results)
- [ ] Performance tuning (batch vector operations, index optimization)
- [ ] Better error messages for API key/connection failures

### v0.2 Features
- [ ] TUI with Textual (browse tiers, live search, token cost visualization)
- [ ] `cre lint` — contradiction detection, orphan chunks, stale tier alerts
- [ ] `cre sync` — watch directory, auto-ingest on changes
- [ ] Export formats (JSON, XML, plain text)

### v0.3 Vision
- [ ] ARIA OS integration (native CLI hook)
- [ ] Browser extension (select text → cre ingest)
- [ ] VS Code extension (cre inject into active context)
- [ ] Web dashboard (optional SaaS layer)

## Running the Skeleton

1. **Install dependencies** (in a venv):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -e ".[dev]"
   ```

2. **Run a command**:
   ```bash
   cre init
   cre ingest README.md
   cre retrieve "Python"
   cre status
   ```

3. **Run tests**:
   ```bash
   pytest tests/
   pytest tests/ --cov=cre
   ```

---

**Built by**: Claude Code
**Date**: 2026-04-10
**Status**: Skeleton complete, all v0.1 features implemented

The engine is ready. 🔥
