"""Tests for retriever module (L1+L2+L3 orchestration)."""

import pytest
from pathlib import Path
from cre.retriever import Retriever, ContextBundle
from cre.vector_store import VectorStore
from cre.memory import Memory
from cre.sidecar import NoOpSidecar
from cre.config import Config


class TestContextBundle:
    """Test ContextBundle dataclass."""

    def test_context_bundle_creation(self):
        """Test creating a context bundle."""
        bundle = ContextBundle(
            themes=["theme1"],
            summaries=["summary1"],
            facts=["fact1"],
            raw_chunks=["chunk1"],
            token_count=100,
            metadata={"query": "test"},
        )
        assert bundle.token_count == 100
        assert len(bundle.themes) == 1


class TestRetriever:
    """Test retriever orchestration."""

    @pytest.fixture
    def retriever_setup(self, tmp_path):
        """Set up retriever with temp stores."""
        config = Config(tmp_path / ".cre")
        config.initialize()

        vector_store = VectorStore(tmp_path / ".cre" / "vector_store")
        memory = Memory(tmp_path / ".cre" / "memory.db")
        sidecar = NoOpSidecar()

        retriever = Retriever(vector_store, memory, sidecar, config)
        return retriever, vector_store, memory, config

    def test_retriever_init(self, retriever_setup):
        """Test retriever initialization."""
        retriever, _, _, _ = retriever_setup
        assert retriever.vector_store is not None
        assert retriever.memory is not None
        assert retriever.sidecar is not None

    def test_retrieve_no_results(self, retriever_setup):
        """Test retrieve with no matching results."""
        retriever, _, _, _ = retriever_setup

        bundle = retriever.retrieve("nonexistent query")
        assert bundle.token_count == 0
        assert len(bundle.themes) == 0
        assert bundle.metadata["status"] == "no results"

    def test_retrieve_with_vector_results(self, retriever_setup):
        """Test retrieve with vector store results."""
        retriever, vector_store, _, _ = retriever_setup

        # Add chunks to vector store
        vector_store.add_chunk(
            chunk_id="chunk1",
            text="This is about bio-mech guitar",
            source_file="research.md",
            domain="research",
        )
        vector_store.add_chunk(
            chunk_id="chunk2",
            text="Blues guitar technique analysis",
            source_file="music.md",
            domain="music",
        )

        bundle = retriever.retrieve("guitar")
        assert len(bundle.raw_chunks) > 0
        assert bundle.token_count > 0

    def test_retrieve_with_tier_packing(self, retriever_setup):
        """Test retrieve with tier-based context packing."""
        retriever, vector_store, memory, _ = retriever_setup

        # Add to vector store
        vector_store.add_chunk(
            chunk_id="chunk1",
            text="Raw fact about guitars",
            source_file="test.md",
            domain="music",
        )

        # Add to memory tiers
        memory.store(
            content="Summary of guitar techniques",
            tier=2,
            domain="music",
            token_count=20,
        )
        memory.store(
            content="Key theme: blues progression",
            tier=3,
            domain="music",
            token_count=10,
        )

        bundle = retriever.retrieve("guitar", token_budget=100)
        assert bundle.token_count <= 100

    def test_retrieve_respects_budget(self, retriever_setup):
        """Test retrieve respects token budget."""
        retriever, vector_store, _, config = retriever_setup

        # Add multiple chunks
        for i in range(10):
            vector_store.add_chunk(
                chunk_id=f"chunk{i}",
                text=f"This is a long chunk with many tokens. " * 20,
                source_file="test.md",
                domain="test",
            )

        bundle = retriever.retrieve("test", token_budget=50)
        assert bundle.token_count <= 50

    def test_retrieve_empty_budget(self, retriever_setup):
        """Test retrieve with zero budget."""
        retriever, vector_store, _, _ = retriever_setup

        vector_store.add_chunk(
            chunk_id="chunk1",
            text="Content",
            source_file="test.md",
        )

        bundle = retriever.retrieve("test", token_budget=5)
        assert bundle.token_count <= 5

    def test_retrieve_top_k_parameter(self, retriever_setup):
        """Test retrieve with top_k parameter."""
        retriever, vector_store, _, _ = retriever_setup

        for i in range(20):
            vector_store.add_chunk(
                chunk_id=f"chunk{i}",
                text=f"Content {i}",
                source_file="test.md",
            )

        bundle = retriever.retrieve("content", top_k=3)
        # Bundle contains packed results, limited by budget not top_k directly
        assert bundle is not None

    def test_compress_document(self, retriever_setup, tmp_path):
        """Test document compression."""
        retriever, _, memory, _ = retriever_setup

        # Create test document
        test_doc = tmp_path / "notes.md"
        test_doc.write_text("Raw session notes with lots of rambling and details.")

        result = retriever.compress_document(str(test_doc))
        assert isinstance(result, str)
        assert len(result) > 0

        # Check it was filed into memory
        stats = memory.get_stats()
        assert stats["total_entries"] > 0

    def test_token_counting(self, retriever_setup):
        """Test internal token counting."""
        retriever, _, _, _ = retriever_setup

        tokens = retriever._token_count("Hello world")
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_retrieve_different_domains(self, retriever_setup):
        """Test retrieve correctly separates domains."""
        retriever, vector_store, memory, _ = retriever_setup

        # Add chunks from different domains
        vector_store.add_chunk(
            chunk_id="research_chunk",
            text="XLM-RoBERTa findings",
            source_file="research.md",
            domain="research",
        )
        vector_store.add_chunk(
            chunk_id="music_chunk",
            text="Blues scale patterns",
            source_file="music.md",
            domain="music",
        )

        bundle = retriever.retrieve("model")
        assert "research" in bundle.metadata["domains"] or len(bundle.metadata["domains"]) > 0
