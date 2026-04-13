"""Per-user workspace path resolution and CRE object factory.

Each API key gets its own isolated workspace directory under WORKSPACE_BASE.
The key is hashed with SHA-256 so raw keys are never stored on disk.

# v0.2: point CRE_WORKSPACE_BASE to Railway Volume for persistence
"""

import os
import hashlib
from pathlib import Path

from cre.config import Config
from cre.vector_store import VectorStore
from cre.memory import Memory


# v0.2: point CRE_WORKSPACE_BASE to Railway Volume for persistence
WORKSPACE_BASE = Path(os.getenv("CRE_WORKSPACE_BASE", "/tmp/cre_workspaces"))


def get_workspace_path(api_key: str) -> Path:
    """Return (and create) the workspace directory for a given API key.

    Uses a 16-char hex prefix of SHA-256(api_key) so raw keys are never
    stored on disk.
    """
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
    workspace = WORKSPACE_BASE / key_hash
    # The .cre sub-directory is what Config expects as cre_dir
    cre_dir = workspace / ".cre"
    cre_dir.mkdir(parents=True, exist_ok=True)
    return workspace


def build_config(workspace: Path) -> Config:
    """Build a CRE Config pointed at a workspace's .cre directory."""
    return Config(cre_dir=workspace / ".cre")


def build_vector_store(workspace: Path) -> VectorStore:
    """Build a VectorStore whose ChromaDB data lives inside the workspace."""
    persist_dir = workspace / ".cre" / "vector_store"
    persist_dir.mkdir(parents=True, exist_ok=True)
    return VectorStore(persist_dir=persist_dir)


def build_memory(workspace: Path) -> Memory:
    """Build a Memory (SQLite) whose db lives inside the workspace."""
    db_path = workspace / ".cre" / "memory.db"
    return Memory(db_path=db_path)
