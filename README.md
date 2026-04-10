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
Pluggable compression and ranking backends. Pick any LLM provider:

| Provider | Model | Cost | Use Case | Speed |
|----------|-------|------|----------|-------|
| **Anthropic** | Claude Haiku | $0.80/1M tokens | Best all-rounder | ⭐⭐⭐ |
| **Groq** | Mixtral 8x7B | Free (beta) | Ultra-fast inference | ⭐⭐⭐⭐⭐ |
| **Google Gemini** | Gemini 2.0 Flash | $0.075/1M tokens | Reasoning-focused | ⭐⭐⭐⭐ |
| **OpenAI** | GPT-4o-mini | $0.15/1M tokens | Most capable | ⭐⭐⭐ |
| **OpenRouter** | 100+ models | Variable | Maximum choice | Varies |
| **Ollama** | Local (Mistral, Phi-3) | Free | Private, offline | ⭐⭐ |
| **None** | - | Free | Vector+memory only | N/A |

**Why provider-agnostic?**
- You control your costs (free models available)
- Lock-in free (switch backends anytime)
- Different projects, different priorities (speed vs cost vs capability)

## Configuration

Edit `.cre/config.yaml` to choose your sidecar backend:

### Groq (Recommended: Free + Ultra-Fast)
```yaml
version: '0.1'

sidecar:
  backend: groq
  model: mixtral-8x7b-32768
  api_key_env: GROQ_API_KEY

embedding:
  model: all-MiniLM-L6-v2
  chunk_size: 512
  chunk_overlap: 64

memory:
  default_inject_budget: 2000
  tier_weights: [0.5, 0.35, 0.15]
```

### Anthropic Claude (Default: Most Balanced)
```yaml
sidecar:
  backend: anthropic
  model: claude-haiku-4-5
  api_key_env: ANTHROPIC_API_KEY
```

### Google Gemini (Reasoning-Focused)
```yaml
sidecar:
  backend: gemini
  model: gemini-2.0-flash
  api_key_env: GOOGLE_API_KEY
```

### OpenAI GPT (Most Capable)
```yaml
sidecar:
  backend: openai
  model: gpt-4o-mini
  api_key_env: OPENAI_API_KEY
```

### OpenRouter (100+ Models)
```yaml
sidecar:
  backend: openrouter
  model: mistralai/mistral-7b-instruct
  api_key_env: OPENROUTER_API_KEY
```

### Ollama (Local, Private, Free)
```yaml
sidecar:
  backend: ollama
  model: mistral
  api_key_env: ""  # Ollama runs locally
```

### Vector+Memory Only (No LLM Cost)
```yaml
sidecar:
  backend: none
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
- ✅ L3 pluggable sidecar backends:
  - Anthropic Claude (default)
  - OpenAI GPT
  - Groq (free, ultra-fast)
  - Google Gemini (reasoning)
  - OpenRouter (100+ models)
  - Ollama (local, private)
  - None (L1+L2 only)
- ✅ Retriever orchestration
- ✅ Context injection
- ✅ CLI commands (8 total)

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

Built by Porjanya Bordoloi (Paul)

*The missing layer between your knowledge and your token window.*
