"""Retriever: Orchestrates L1 (vector), L2 (memory), L3 (sidecar) to retrieve context."""

from typing import List, Dict, Any, Optional
import tiktoken
from dataclasses import dataclass


@dataclass
class ContextBundle:
    """Packed context ready for injection into LLM prompt."""

    themes: List[str]
    summaries: List[str]
    facts: List[str]
    raw_chunks: List[str]
    token_count: int
    metadata: Dict[str, Any]


class Retriever:
    """Orchestrate L1 + L2 + L3 to retrieve and pack context within token budget."""

    def __init__(self, vector_store, memory, sidecar, config):
        """Initialize retriever.

        Args:
            vector_store: L1 VectorStore
            memory: L2 Memory
            sidecar: L3 Sidecar backend
            config: Config object
        """
        self.vector_store = vector_store
        self.memory = memory
        self.sidecar = sidecar
        self.config = config
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def _token_count(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.encoding.encode(text))

    def retrieve(
        self,
        query: str,
        token_budget: Optional[int] = None,
        top_k: int = 5,
    ) -> ContextBundle:
        """Retrieve and pack context within token budget.

        Args:
            query: Query string
            token_budget: Max tokens to include (defaults to config)
            top_k: Top K chunks to retrieve from L1

        Returns:
            ContextBundle ready for injection
        """
        token_budget = token_budget or self.config.default_inject_budget

        # Step 1: L1 vector search
        vector_results = self.vector_store.retrieve(query, top_k=top_k)
        if not vector_results:
            return ContextBundle(
                themes=[], summaries=[], facts=[], raw_chunks=[],
                token_count=0, metadata={"status": "no results"}
            )

        # Step 2: L2 tier fetch - get summaries and themes for matching domains
        domains = set()
        for result in vector_results:
            domain = result["metadata"].get("domain")
            if domain:
                domains.add(domain)

        themes = []
        summaries = []
        for domain in domains:
            themes.extend(self.memory.retrieve_by_domain(domain, tier=3, limit=5))
            summaries.extend(self.memory.retrieve_by_domain(domain, tier=2, limit=10))

        # Step 3: L3 sidecar rank (optional compression)
        raw_chunks = [r["text"] for r in vector_results]
        if len(raw_chunks) > 1 and not isinstance(self.sidecar, type(self.sidecar)) or self.sidecar.__class__.__name__ != "NoOpSidecar":
            try:
                ranked = self.sidecar.rank(query, raw_chunks)
                raw_chunks = ranked
            except Exception:
                # Fall back to original order if ranking fails
                pass

        # Step 4: Budget-aware tier selection
        # Tier weights: [themes, summaries, facts]
        weights = self.config.tier_weights  # [0.5, 0.35, 0.15]
        tier_budgets = [
            int(token_budget * weights[0]),  # themes
            int(token_budget * weights[1]),  # summaries
            int(token_budget * weights[2]),  # facts
        ]

        packed_themes = []
        packed_summaries = []
        packed_facts = []
        total_tokens = 0

        # Pack themes first
        for theme in themes:
            content = theme["content"]
            tokens = theme.get("token_count", self._token_count(content))
            if total_tokens + tokens <= tier_budgets[0]:
                packed_themes.append(content)
                total_tokens += tokens
            else:
                break

        # Pack summaries second
        for summary in summaries:
            content = summary["content"]
            tokens = summary.get("token_count", self._token_count(content))
            if total_tokens + tokens <= tier_budgets[0] + tier_budgets[1]:
                packed_summaries.append(content)
                total_tokens += tokens
            else:
                break

        # Pack raw facts/chunks last
        for chunk in raw_chunks:
            tokens = self._token_count(chunk)
            if total_tokens + tokens <= token_budget:
                packed_facts.append(chunk)
                total_tokens += tokens
            else:
                break

        metadata = {
            "query": query,
            "token_budget": token_budget,
            "vector_results": len(vector_results),
            "domains": list(domains),
            "status": "ok",
        }

        return ContextBundle(
            themes=packed_themes,
            summaries=packed_summaries,
            facts=packed_facts,
            raw_chunks=packed_facts,
            token_count=total_tokens,
            metadata=metadata,
        )

    def compress_document(self, file_path: str, tier: int = 2) -> str:
        """Compress/summarize a document and file into memory.

        Args:
            file_path: Path to document
            tier: Target memory tier (2=summary, 3=theme)

        Returns:
            Compressed text
        """
        with open(file_path, "r") as f:
            text = f.read()

        compressed = self.sidecar.compress(text)
        token_count = self._token_count(compressed)

        # File into memory
        self.memory.store(
            content=compressed,
            tier=tier,
            source_file=file_path,
            token_count=token_count,
        )

        return compressed
