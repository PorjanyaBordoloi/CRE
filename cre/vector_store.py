"""L1: ChromaDB vector store with sentence-transformers embeddings."""

from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import chromadb


class VectorStore:
    """Wrapper around ChromaDB for semantic search and chunk storage."""

    def __init__(self, persist_dir: Optional[Path] = None):
        """Initialize ChromaDB vector store.

        Args:
            persist_dir: Directory for persistent storage. Defaults to .cre/vector_store/
        """
        self.persist_dir = persist_dir or Path.cwd() / ".cre" / "vector_store"
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistence (new API 0.5+)
        self.client = chromadb.PersistentClient(path=str(self.persist_dir))
        self.collection = self.client.get_or_create_collection(
            name="documents",
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunk(
        self,
        chunk_id: str,
        text: str,
        source_file: str,
        domain: str = "",
        tier_hint: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a chunk to the vector store.

        Args:
            chunk_id: Unique chunk identifier
            text: Chunk content
            source_file: Path to source file
            domain: Domain classification (research, academics, music, self, synthesis, aria)
            tier_hint: Suggested tier (1=raw, 2=summary, 3=theme)
            metadata: Additional metadata
        """
        meta = metadata or {}
        meta.update(
            {
                "source_file": source_file,
                "domain": domain,
                "tier_hint": tier_hint,
                "created_at": datetime.utcnow().isoformat(),
            }
        )

        self.collection.add(
            ids=[chunk_id],
            documents=[text],
            metadatas=[meta],
        )

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-K chunks for a query.

        Args:
            query: Query string
            top_k: Number of top results to return

        Returns:
            List of dicts with keys: id, text, score, metadata
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            include=["embeddings", "documents", "metadatas", "distances"],
        )

        chunks = []
        if results and results["ids"] and len(results["ids"]) > 0:
            for idx, chunk_id in enumerate(results["ids"][0]):
                # ChromaDB returns distances; convert to similarity scores
                score = 1 - (results["distances"][0][idx] / 2)  # normalize cosine distance
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": results["documents"][0][idx],
                        "score": score,
                        "metadata": results["metadatas"][0][idx],
                    }
                )

        return chunks

    def count(self) -> int:
        """Get total chunk count in vector store."""
        return self.collection.count()

    def delete_chunk(self, chunk_id: str) -> None:
        """Delete a chunk by ID."""
        self.collection.delete(ids=[chunk_id])

    def clear(self) -> None:
        """Clear all chunks from vector store."""
        self.collection.delete(where={})

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        return {
            "total_chunks": self.count(),
            "persist_dir": str(self.persist_dir),
        }
