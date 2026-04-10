"""Tests for ingestor module (file reading, chunking, embedding)."""

import pytest
from pathlib import Path
import tempfile
from cre.ingestor import Chunker, Ingestor, count_tokens
from cre.vector_store import VectorStore
from cre.memory import Memory


class TestChunker:
    """Test sliding window chunker."""

    def test_chunker_init(self):
        """Test chunker initialization."""
        chunker = Chunker(chunk_size=512, chunk_overlap=64)
        assert chunker.chunk_size == 512
        assert chunker.chunk_overlap == 64

    def test_token_count(self):
        """Test token counting."""
        text = "Hello world"
        tokens = count_tokens(text)
        assert isinstance(tokens, int)
        assert tokens > 0

    def test_chunk_short_text(self):
        """Test chunking short text."""
        chunker = Chunker(chunk_size=100, chunk_overlap=10)
        text = "This is a short paragraph. It has multiple sentences."
        chunks = chunker.chunk(text)
        assert len(chunks) > 0
        for chunk_text, token_count in chunks:
            assert isinstance(chunk_text, str)
            assert isinstance(token_count, int)

    def test_chunk_long_text(self):
        """Test chunking longer text."""
        chunker = Chunker(chunk_size=50, chunk_overlap=5)
        text = " ".join(["word"] * 100)
        chunks = chunker.chunk(text)
        assert len(chunks) > 0


class TestIngestor:
    """Test file ingestor."""

    @pytest.fixture
    def ingestor_setup(self, tmp_path):
        """Set up ingestor with temp stores."""
        vector_store = VectorStore(tmp_path / "vector_store")
        memory = Memory(tmp_path / "memory.db")
        ingestor = Ingestor(vector_store, memory)
        return ingestor, tmp_path

    def test_ingestor_init(self, ingestor_setup):
        """Test ingestor initialization."""
        ingestor, _ = ingestor_setup
        assert ingestor.vector_store is not None
        assert ingestor.memory is not None
        assert ingestor.chunker is not None

    def test_ingest_file(self, ingestor_setup):
        """Test ingesting a single markdown file."""
        ingestor, tmp_path = ingestor_setup

        # Create test markdown file
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test paragraph.")

        chunk_ids = ingestor.ingest_file(test_file)
        assert len(chunk_ids) > 0
        assert all(isinstance(cid, str) for cid in chunk_ids)

    def test_ingest_directory(self, ingestor_setup):
        """Test ingesting a directory of markdown files."""
        ingestor, tmp_path = ingestor_setup

        # Create test markdown files
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "file1.md").write_text("# File 1\n\nContent here.")
        (tmp_path / "docs" / "file2.md").write_text("# File 2\n\nMore content.")

        chunk_ids = ingestor.ingest_directory(tmp_path / "docs")
        assert len(chunk_ids) > 0

    def test_ingest_with_domain(self, ingestor_setup):
        """Test ingesting with domain classification."""
        ingestor, tmp_path = ingestor_setup

        test_file = tmp_path / "research.md"
        test_file.write_text("# Research Note\n\nBio-mech guitar findings.")

        chunk_ids = ingestor.ingest_file(test_file, domain="research")
        assert len(chunk_ids) > 0

    def test_ingest_nonexistent_file(self, ingestor_setup):
        """Test ingesting nonexistent file raises error."""
        ingestor, tmp_path = ingestor_setup

        with pytest.raises(FileNotFoundError):
            ingestor.ingest_file(tmp_path / "nonexistent.md")

    def test_ingest_nonexistent_directory(self, ingestor_setup):
        """Test ingesting nonexistent directory raises error."""
        ingestor, tmp_path = ingestor_setup

        with pytest.raises(NotADirectoryError):
            ingestor.ingest_directory(tmp_path / "nonexistent")
