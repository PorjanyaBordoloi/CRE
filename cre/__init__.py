"""Context Retrieval Engine - Composable context management for LLM workflows."""

__version__ = "0.1.0"
__author__ = "Porjanya Bordoloi"

from cre.config import Config
from cre.vector_store import VectorStore
from cre.memory import Memory
from cre.sidecar import get_sidecar
from cre.retriever import Retriever

__all__ = [
    "Config",
    "VectorStore",
    "Memory",
    "get_sidecar",
    "Retriever",
]
