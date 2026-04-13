# CLAUDE_API.md — CRE API Layer Build Instructions

> **Companion file to `CLAUDE.md`** (which covers CRE core build/setup).
> This file covers ONLY the API layer. Do not modify anything inside `cre/` — only wrap it.
> Goal: Wrap the existing CRE CLI engine into a production-ready FastAPI service, deployable on Railway.

---

## Project Context

CRE (Context Retrieval Engine) is a composable, model-agnostic CLI tool that sits between a knowledge base and an LLM — compressing, tiering, and injecting only the context that matters.

Current state: CLI tool (`cre init`, `cre ingest`, `cre retrieve`, `cre inject`, `cre compress`, `cre status`)
Target state: REST API exposing all CLI functionality with API key auth + per-user workspace isolation

---

## Phase 1 — Project Structure Setup

Create the following new files/folders alongside the existing `cre/` directory:

```
CRE/
├── cre/                    # existing — do not modify
├── tests/                  # existing — do not modify
├── api/
│   ├── __init__.py
│   ├── main.py             # FastAPI app entrypoint
│   ├── auth.py             # API key validation middleware
│   ├── workspace.py        # Per-user workspace path resolution
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ingest.py       # POST /ingest
│   │   ├── retrieve.py     # POST /retrieve
│   │   ├── inject.py       # POST /inject
│   │   ├── compress.py     # POST /compress
│   │   └── status.py       # GET /status
│   └── models/
│       ├── __init__.py
│       └── schemas.py      # Pydantic request/response schemas
├── Dockerfile
├── railway.toml
├── .env.example
└── requirements-api.txt
```

---

## Phase 2 — Core Files to Build

### `api/main.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import ingest, retrieve, inject, compress, status

app = FastAPI(
    title="CRE API",
    description="Context Retrieval Engine — REST API layer. Never waste tokens on context management again.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/v1", tags=["Ingest"])
app.include_router(retrieve.router, prefix="/v1", tags=["Retrieve"])
app.include_router(inject.router, prefix="/v1", tags=["Inject"])
app.include_router(compress.router, prefix="/v1", tags=["Compress"])
app.include_router(status.router, prefix="/v1", tags=["Status"])

@app.get("/")
def root():
    return {
        "service": "CRE API",
        "version": "0.1.0",
        "docs": "/docs",
        "github": "https://github.com/PorjanyaBordoloi/CRE"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

### `api/auth.py`

```python
import os
import secrets
import hashlib
from fastapi import Header, HTTPException, status

# In production: replace with a database lookup
# For v0.1: use environment variable API keys (comma-separated)
# Format in .env: API_KEYS=key1,key2,key3

def get_api_keys() -> set:
    raw = os.getenv("API_KEYS", "")
    return set(k.strip() for k in raw.split(",") if k.strip())

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    valid_keys = get_api_keys()
    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key store not configured on server."
        )
    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key."
        )
    return x_api_key

def generate_api_key() -> str:
    """Utility to generate a new API key. Use in admin scripts."""
    return secrets.token_urlsafe(32)
```

---

### `api/workspace.py`

```python
import os
import hashlib
from pathlib import Path

# Each API key gets its own isolated workspace directory
# Workspaces are stored under /tmp/cre_workspaces/<hashed_key>/

WORKSPACE_BASE = Path(os.getenv("CRE_WORKSPACE_BASE", "/tmp/cre_workspaces"))

def get_workspace_path(api_key: str) -> Path:
    """
    Returns the workspace path for a given API key.
    Uses a hash of the key so raw keys are never stored on disk.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    workspace = WORKSPACE_BASE / key_hash
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace
```

---

### `api/models/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal

# --- Ingest ---
class IngestRequest(BaseModel):
    content: str = Field(..., description="Text content to ingest into CRE")
    domain: Optional[str] = Field("general", description="Domain label (e.g. research, self, project)")
    tier: Optional[int] = Field(1, ge=1, le=3, description="Initial memory tier (1=raw, 2=summary, 3=theme)")

class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    domain: str
    tier: int

# --- Retrieve ---
class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Natural language query to retrieve context for")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to return")

class RetrieveResponse(BaseModel):
    query: str
    results: list
    token_estimate: int

# --- Inject ---
class InjectRequest(BaseModel):
    query: str = Field(..., description="Query to retrieve and format for prompt injection")
    budget: Optional[int] = Field(2000, ge=100, le=8000, description="Token budget for injected context")
    format: Optional[Literal["markdown", "xml", "plain"]] = Field("markdown", description="Output format")

class InjectResponse(BaseModel):
    query: str
    injected_context: str
    token_count: int
    budget: int
    format: str

# --- Compress ---
class CompressRequest(BaseModel):
    content: str = Field(..., description="Session log or document text to compress")
    target_tier: Optional[int] = Field(2, ge=2, le=3, description="Target compression tier")

class CompressResponse(BaseModel):
    status: str
    original_length: int
    compressed_length: int
    target_tier: int
    summary: str

# --- Status ---
class StatusResponse(BaseModel):
    workspace_id: str
    vector_store_count: int
    memory_tier1_count: int
    memory_tier2_count: int
    memory_tier3_count: int
    total_chunks: int
```

---

### `api/routes/ingest.py`

```python
import os
import tempfile
from fastapi import APIRouter, Depends
from api.auth import verify_api_key
from api.workspace import get_workspace_path
from api.models.schemas import IngestRequest, IngestResponse

# Import CRE internals directly (avoid subprocess overhead)
from cre.ingestor import Ingestor
from cre.config import CREConfig

router = APIRouter()

@router.post("/ingest", response_model=IngestResponse)
async def ingest_content(
    request: IngestRequest,
    api_key: str = Depends(verify_api_key)
):
    workspace = get_workspace_path(api_key)
    
    # Write content to temp file, ingest, clean up
    with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        f.write(request.content)
        temp_path = f.name
    
    try:
        config = CREConfig(workspace_dir=str(workspace))
        ingestor = Ingestor(config)
        result = ingestor.ingest_file(temp_path, domain=request.domain, tier=request.tier)
        chunks = result.get("chunks", 0)
    finally:
        os.unlink(temp_path)
    
    return IngestResponse(
        status="ok",
        chunks_ingested=chunks,
        domain=request.domain,
        tier=request.tier
    )
```

---

### `api/routes/retrieve.py`

```python
from fastapi import APIRouter, Depends
from api.auth import verify_api_key
from api.workspace import get_workspace_path
from api.models.schemas import RetrieveRequest, RetrieveResponse
from cre.retriever import Retriever
from cre.config import CREConfig

router = APIRouter()

@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_context(
    request: RetrieveRequest,
    api_key: str = Depends(verify_api_key)
):
    workspace = get_workspace_path(api_key)
    config = CREConfig(workspace_dir=str(workspace))
    retriever = Retriever(config)
    
    results = retriever.retrieve(request.query, top_k=request.top_k)
    
    # Rough token estimate: 1 token ≈ 4 chars
    token_estimate = sum(len(str(r)) for r in results) // 4
    
    return RetrieveResponse(
        query=request.query,
        results=results,
        token_estimate=token_estimate
    )
```

---

### `api/routes/inject.py`

```python
from fastapi import APIRouter, Depends
from api.auth import verify_api_key
from api.workspace import get_workspace_path
from api.models.schemas import InjectRequest, InjectResponse
from cre.injector import Injector
from cre.config import CREConfig

router = APIRouter()

@router.post("/inject", response_model=InjectResponse)
async def inject_context(
    request: InjectRequest,
    api_key: str = Depends(verify_api_key)
):
    workspace = get_workspace_path(api_key)
    config = CREConfig(workspace_dir=str(workspace))
    injector = Injector(config)
    
    context_block = injector.inject(
        query=request.query,
        budget=request.budget,
        format=request.format
    )
    
    token_count = len(context_block) // 4
    
    return InjectResponse(
        query=request.query,
        injected_context=context_block,
        token_count=token_count,
        budget=request.budget,
        format=request.format
    )
```

---

### `api/routes/compress.py`

```python
import tempfile, os
from fastapi import APIRouter, Depends
from api.auth import verify_api_key
from api.workspace import get_workspace_path
from api.models.schemas import CompressRequest, CompressResponse
from cre.memory import Memory
from cre.config import CREConfig

router = APIRouter()

@router.post("/compress", response_model=CompressResponse)
async def compress_content(
    request: CompressRequest,
    api_key: str = Depends(verify_api_key)
):
    workspace = get_workspace_path(api_key)
    config = CREConfig(workspace_dir=str(workspace))
    memory = Memory(config)
    
    result = memory.compress(request.content, target_tier=request.target_tier)
    
    return CompressResponse(
        status="ok",
        original_length=len(request.content),
        compressed_length=len(result.get("summary", "")),
        target_tier=request.target_tier,
        summary=result.get("summary", "")
    )
```

---

### `api/routes/status.py`

```python
import hashlib
from fastapi import APIRouter, Depends
from api.auth import verify_api_key
from api.workspace import get_workspace_path
from api.models.schemas import StatusResponse
from cre.vector_store import VectorStore
from cre.memory import Memory
from cre.config import CREConfig

router = APIRouter()

@router.get("/status", response_model=StatusResponse)
async def get_status(api_key: str = Depends(verify_api_key)):
    workspace = get_workspace_path(api_key)
    workspace_id = hashlib.sha256(api_key.encode()).hexdigest()[:8]
    
    config = CREConfig(workspace_dir=str(workspace))
    vs = VectorStore(config)
    mem = Memory(config)
    
    vs_count = vs.count()
    t1 = mem.count_tier(1)
    t2 = mem.count_tier(2)
    t3 = mem.count_tier(3)
    
    return StatusResponse(
        workspace_id=workspace_id,
        vector_store_count=vs_count,
        memory_tier1_count=t1,
        memory_tier2_count=t2,
        memory_tier3_count=t3,
        total_chunks=vs_count + t1 + t2 + t3
    )
```

---

## Phase 2b — Sidecar Option C (Server Default + Per-Request Override)

This is the sidecar flexibility layer. Server default is Groq — works out of the box with zero
extra headers. Any caller can override with their own backend per-request.

### `api/sidecar_resolver.py`

```python
import os
from fastapi import Header
from typing import Optional
from cre.sidecar import get_sidecar, SidecarBackend

DEFAULT_BACKEND = os.getenv("CRE_DEFAULT_SIDECAR_BACKEND", "groq")
DEFAULT_MODEL_MAP = {
    "groq":      "mixtral-8x7b-32768",
    "anthropic": "claude-haiku-4-5",
    "openai":    "gpt-4o-mini",
    "gemini":    "gemini-2.0-flash",
    "ollama":    "mistral",
    "none":      None,
}
DEFAULT_KEY_ENV_MAP = {
    "groq":      "GROQ_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "gemini":    "GOOGLE_API_KEY",
    "ollama":    "",
    "none":      "",
}

def resolve_sidecar(
    x_sidecar_backend: Optional[str] = Header(None, alias="X-Sidecar-Backend"),
    x_sidecar_api_key: Optional[str] = Header(None, alias="X-Sidecar-API-Key"),
) -> SidecarBackend:
    """
    Priority:
      1. Per-request headers (X-Sidecar-Backend + X-Sidecar-API-Key)
      2. Server default (CRE_DEFAULT_SIDECAR_BACKEND, defaults to groq)
      3. Falls back to NoOpSidecar if no key available anywhere
    """
    backend = (x_sidecar_backend or DEFAULT_BACKEND).lower().strip()
    model = DEFAULT_MODEL_MAP.get(backend, DEFAULT_MODEL_MAP[DEFAULT_BACKEND])

    if x_sidecar_api_key:
        api_key = x_sidecar_api_key
    else:
        key_env = DEFAULT_KEY_ENV_MAP.get(backend, "")
        api_key = os.getenv(key_env, "") if key_env else ""

    # Graceful fallback if key missing
    if not api_key and backend not in ("ollama", "none"):
        backend = "none"
        model = None

    return get_sidecar(backend=backend, model=model, api_key=api_key)
```

### Inject as a FastAPI dependency in routes that need it

```python
from api.sidecar_resolver import resolve_sidecar
from cre.sidecar import SidecarBackend

@router.post("/inject", response_model=InjectResponse)
async def inject_context(
    request: InjectRequest,
    api_key: str = Depends(verify_api_key),
    sidecar: SidecarBackend = Depends(resolve_sidecar)
):
    # pass sidecar into Retriever/Injector
    ...
```

### Three caller patterns (document these in README)

```bash
# 1. No headers — uses server Groq default. Zero friction for Sarvam AI demo.
curl -X POST "$BASE_URL/v1/inject" -H "X-API-Key: $KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "context retrieval", "budget": 2000}'

# 2. Override — caller brings their own Anthropic key
curl -X POST "$BASE_URL/v1/inject" -H "X-API-Key: $KEY" \
  -H "X-Sidecar-Backend: anthropic" \
  -H "X-Sidecar-API-Key: sk-ant-their-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "context retrieval", "budget": 2000}'

# 3. Free local — Ollama, no key needed
curl -X POST "$BASE_URL/v1/inject" -H "X-API-Key: $KEY" \
  -H "X-Sidecar-Backend: ollama" \
  -H "Content-Type: application/json" \
  -d '{"query": "context retrieval", "budget": 2000}'
```

---

## Phase 3 — Deployment Files

### `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System deps for ChromaDB + sentence-transformers
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install CRE + API deps
COPY pyproject.toml .
COPY requirements-api.txt .
RUN pip install --no-cache-dir -e . && \
    pip install --no-cache-dir -r requirements-api.txt

# Copy source
COPY cre/ ./cre/
COPY api/ ./api/

# Railway sets PORT env var automatically
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

### `railway.toml`

```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn api.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

[[services]]
name = "cre-api"
```

---

### `requirements-api.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
python-multipart>=0.0.9
pydantic>=2.0.0
python-dotenv>=1.0.0
```

---

### `.env.example`

```env
# CRE API Configuration
# Copy this to .env and fill in values

# ── Auth ──────────────────────────────────────────────
# Comma-separated API keys for callers
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
API_KEYS=your_api_key_here,another_key_here

# ── Sidecar LLM (server default) ──────────────────────
# Default backend used when caller sends no X-Sidecar-Backend header
# Options: groq | anthropic | openai | gemini | ollama | none
CRE_DEFAULT_SIDECAR_BACKEND=groq

# Fill in the key for whichever backend is set as default above
# Callers can override these per-request via X-Sidecar-API-Key header
GROQ_API_KEY=your_groq_key_here
ANTHROPIC_API_KEY=
OPENAI_API_KEY=
GOOGLE_API_KEY=
# Ollama runs locally — no key needed

# ── Storage ───────────────────────────────────────────
# v0.1: ephemeral /tmp (resets on redeploy — fine for demo/pitch)
# v0.2: mount a Railway Volume and point this to the mount path
CRE_WORKSPACE_BASE=/tmp/cre_workspaces
```

---

## Phase 4 — CREConfig Compatibility Check

Before running the API, Claude Code must verify that the existing `cre/config.py` accepts a `workspace_dir` parameter.

Run this check:
```bash
grep -n "workspace_dir\|__init__" cre/config.py
```

If `CREConfig` does not accept `workspace_dir`, add support:
```python
# In cre/config.py — add workspace_dir param to __init__
def __init__(self, workspace_dir: str = None):
    if workspace_dir:
        self.base_dir = Path(workspace_dir)
    else:
        self.base_dir = Path(".cre")
    # rest of existing init...
```

---

## Phase 5 — Railway Deploy Steps

After all files are created and tested locally:

```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Initialize project (run from repo root)
railway init

# 4. Set environment variables
railway variables set API_KEYS="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
railway variables set CRE_DEFAULT_SIDECAR_BACKEND="groq"
railway variables set GROQ_API_KEY="your_groq_key_here"
# Optional: add other keys so callers can override to them
# railway variables set ANTHROPIC_API_KEY="sk-ant-..."
# railway variables set OPENAI_API_KEY="sk-..."

# 5. Deploy
railway up

# 6. Get your live URL
railway open
```

---

## Phase 6 — Smoke Test After Deploy

```bash
# Replace with your Railway URL and generated API key
BASE_URL="https://your-cre-api.railway.app"
API_KEY="your_api_key_here"

# Health check
curl $BASE_URL/health

# Ingest test
curl -X POST "$BASE_URL/v1/ingest" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"content": "CRE is a context retrieval engine with three-layer compression.", "domain": "test"}'

# Retrieve test
curl -X POST "$BASE_URL/v1/retrieve" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "context retrieval", "top_k": 3}'

# Status check
curl "$BASE_URL/v1/status" \
  -H "X-API-Key: $API_KEY"
```

---

## Important Notes for Claude Code

1. **Do not modify anything inside `cre/`** — only wrap it. The CLI must still work as before.
2. **Import CRE modules directly** (not via subprocess) for performance.
3. **If any CRE internal class doesn't expose the needed method**, add a thin adapter inside `api/` — never patch `cre/` itself.
4. **Storage is intentionally ephemeral for v0.1** — both SQLite (L2) and ChromaDB (L1) live under `/tmp/cre_workspaces/<hash>/`. They reset on Railway redeploy. This is acceptable for the Sarvam AI pitch. Add a `# v0.2: point CRE_WORKSPACE_BASE to Railway Volume for persistence` comment wherever workspace path is resolved.
5. **Sidecar default is Groq** — server must have `GROQ_API_KEY` set. If missing, sidecar_resolver falls back to `NoOpSidecar` gracefully — L1+L2 still work, just no LLM ranking/compression.
6. **First Railway deploy will be slow** — sentence-transformer model downloads on first `/v1/ingest` call. Expected behaviour, not a bug.
7. **After all files are created**, run `pytest tests/` to confirm existing CRE tests still pass before deploying.
