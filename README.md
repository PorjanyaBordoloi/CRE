# CRE — Context Retrieval Engine

**Never waste tokens on context management again.**

CRE is a composable, model-agnostic CLI tool that sits between your knowledge base and your LLM — compressing, tiering, and injecting only the context that actually matters.

## Installation

```bash
pip install cre
```

Or from source:

```bash
git clone https://github.com/yourusername/cre.git
cd cre
pip install -e .
```

## Quick Start

### Initialize a project

```bash
cre init
```

Creates `.cre/` directory with config, vector store, and memory database.

### Ingest your knowledge base

```bash
# Ingest a directory of markdown files
cre ingest wiki/ --domain research

# Ingest a single file
cre ingest notes.md --domain self --tier 2
```

### Retrieve relevant context

```bash
# Vector search + tier retrieval
cre retrieve "bio-mech guitar architecture"

# Format for direct prompt injection
cre inject "architecture query" --budget 2000 --format markdown
```

### Compress session logs

```bash
cre compress session.log --tier 2
```

### Check status

```bash
cre status
```

## Architecture

Three independent layers, each powerful on its own, stronger together:

### L1: Vector Store (ChromaDB)
Semantic search over your knowledge base. Sliding window chunking, embedding with sentence-transformers, local persistence.

### L2: Tiered Memory (SQLite)
Structured abstraction:
- **Tier 1 (Raw)**: Verbatim facts, decisions, code snippets
- **Tier 2 (Summaries)**: LLM-compressed paragraph-level summaries
- **Tier 3 (Themes)**: High-level bullet-point themes

### L3: Sidecar LLM
Pluggable compression and ranking backends:
- **Anthropic**: Claude Haiku (cheapest, default)
- **OpenAI**: GPT-4o-mini
- **Ollama**: Local models (Mistral, Phi-3, etc.)
- **None**: L1+L2 only mode (no sidecar cost)

## Configuration

Edit `.cre/config.yaml`:

```yaml
version: '0.1'

sidecar:
  backend: anthropic  # anthropic | openai | ollama | none
  model: claude-haiku-4-5
  api_key_env: ANTHROPIC_API_KEY

embedding:
  model: all-MiniLM-L6-v2
  chunk_size: 512
  chunk_overlap: 64

memory:
  default_inject_budget: 2000
  tier_weights: [0.5, 0.35, 0.15]  # themes, summaries, facts
```

## Commands

| Command | Purpose |
|---------|---------|
| `cre init` | Initialize CRE in a directory |
| `cre ingest <path>` | Ingest markdown files into L1+L2 |
| `cre retrieve <query>` | Vector search + tier fetch |
| `cre inject <query>` | Retrieve + format for prompt injection |
| `cre compress <file>` | Compress document, file into memory |
| `cre status` | Show store statistics |
| `cre tui` | Launch TUI viewer (v0.2) |
| `cre lint` | Health check (v0.2) |

## Data Flow

```
Your Knowledge Base
    ↓
cre ingest
    ├→ L1: ChromaDB (vector embeddings)
    └→ L2: SQLite (tiered memory)
         ↓
    User Query
         ↓
    L1 vector search
    + L2 tier fetch
    + L3 sidecar rank/compress
         ↓
    Token-budgeted context block
         ↓
cre inject → Your LLM Prompt
```

## Why CRE Beats Pure RAG

| Aspect | Pure RAG | CRE |
|--------|----------|-----|
| Semantic retrieval | ✅ | ✅ |
| Structured tiers | ❌ | ✅ |
| Sidecar ranking | ❌ | ✅ |
| Token budgeting | ❌ | ✅ |
| Bidirectional flow | ❌ | ✅ |
| Local-first | ❌ | ✅ |
| Model-agnostic | ❌ | ✅ |

## Development

### Running tests

```bash
pytest tests/
pytest tests/ --cov=cre  # with coverage
```

### Project structure

```
cre/
├── __init__.py
├── cli.py              # Typer CLI entrypoint
├── config.py           # .cre/config.yaml management
├── vector_store.py     # L1: ChromaDB wrapper
├── memory.py           # L2: SQLite tiered memory
├── sidecar.py          # L3: Pluggable LLM backends
├── ingestor.py         # File reading, chunking, embedding
├── retriever.py        # Orchestration (L1+L2+L3)
├── injector.py         # Context formatting
└── tui.py              # TUI (v0.2 stub)

tests/
├── test_ingestor.py
├── test_memory.py
└── test_retriever.py
```

## Roadmap

### v0.1 (Current) — Core Engine
- ✅ L1 vector store (ChromaDB)
- ✅ L2 tiered memory (SQLite)
- ✅ L3 sidecar backends (Anthropic/OpenAI/Ollama)
- ✅ Retriever orchestration
- ✅ Context injection
- ✅ CLI commands

### v0.2 — Polish & Tools
- TUI viewer (Textual)
- `cre lint` — contradictions, orphans, stale tiers
- `cre sync` — watch directory, auto-ingest
- Export formats (JSON, XML, plain text)

### v0.3 — Integration
- ARIA OS native integration
- Browser extension (select + ingest)
- VS Code extension
- Web dashboard

## License

MIT — Open source from day 1.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines, setup, and good first issues.

---

Built by Porjanya Bordoloi (The Flame)
RGU AI & Data Science
*The missing layer between your knowledge and your token window.*
