"""Tests for memory module (SQLite tiered memory)."""

import pytest
from pathlib import Path
from cre.memory import Memory


class TestMemory:
    """Test SQLite tiered memory."""

    @pytest.fixture
    def memory(self, tmp_path):
        """Create memory instance with temp database."""
        db_path = tmp_path / "test_memory.db"
        return Memory(db_path)

    def test_memory_init(self, memory):
        """Test memory initialization."""
        assert memory.db_path.exists()

    def test_store_raw_fact(self, memory):
        """Test storing a raw fact (tier 1)."""
        memory_id = memory.store(
            content="This is a raw fact",
            tier=1,
            domain="research",
            source_file="test.md",
            token_count=5,
        )
        assert memory_id is not None
        assert len(memory_id) > 0

    def test_store_summary(self, memory):
        """Test storing a summary (tier 2)."""
        memory_id = memory.store(
            content="Summary of multiple facts",
            tier=2,
            domain="research",
            source_file="test.md",
            token_count=10,
        )
        assert memory_id is not None

    def test_store_theme(self, memory):
        """Test storing a theme (tier 3)."""
        memory_id = memory.store(
            content="Key theme across findings",
            tier=3,
            domain="research",
            token_count=8,
        )
        assert memory_id is not None

    def test_store_with_tags(self, memory):
        """Test storing with tags."""
        memory_id = memory.store(
            content="Tagged entry",
            tier=1,
            tags=["important", "research"],
        )
        assert memory_id is not None

    def test_retrieve_by_tier(self, memory):
        """Test retrieving memories by tier."""
        memory.store(content="Fact 1", tier=1)
        memory.store(content="Fact 2", tier=1)
        memory.store(content="Summary 1", tier=2)

        tier1 = memory.retrieve_by_tier(1)
        assert len(tier1) == 2

        tier2 = memory.retrieve_by_tier(2)
        assert len(tier2) == 1

    def test_retrieve_by_domain(self, memory):
        """Test retrieving memories by domain."""
        memory.store(content="Research fact", tier=1, domain="research")
        memory.store(content="Music fact", tier=1, domain="music")
        memory.store(content="Research summary", tier=2, domain="research")

        research = memory.retrieve_by_domain("research")
        assert len(research) == 2

        music = memory.retrieve_by_domain("music")
        assert len(music) == 1

    def test_retrieve_by_domain_and_tier(self, memory):
        """Test retrieving by domain and tier."""
        memory.store(content="Research fact", tier=1, domain="research")
        memory.store(content="Research summary", tier=2, domain="research")

        research_tier1 = memory.retrieve_by_domain("research", tier=1)
        assert len(research_tier1) == 1

    def test_retrieve_all(self, memory):
        """Test retrieving all memories."""
        memory.store(content="Entry 1", tier=1)
        memory.store(content="Entry 2", tier=2)
        memory.store(content="Entry 3", tier=3)

        all_entries = memory.retrieve_all()
        assert len(all_entries) == 3

    def test_get_by_id(self, memory):
        """Test retrieving by ID."""
        memory_id = memory.store(content="Specific entry", tier=1)
        entry = memory.get_by_id(memory_id)

        assert entry is not None
        assert entry["content"] == "Specific entry"
        assert entry["tier"] == 1

    def test_delete(self, memory):
        """Test deleting a memory entry."""
        memory_id = memory.store(content="To be deleted", tier=1)
        memory.delete(memory_id)

        entry = memory.get_by_id(memory_id)
        assert entry is None

    def test_count_by_tier(self, memory):
        """Test counting by tier."""
        memory.store(content="Fact 1", tier=1)
        memory.store(content="Fact 2", tier=1)
        memory.store(content="Summary 1", tier=2)

        counts = memory.count_by_tier()
        assert counts.get(1, 0) == 2
        assert counts.get(2, 0) == 1

    def test_count_total(self, memory):
        """Test total count."""
        memory.store(content="Entry 1", tier=1)
        memory.store(content="Entry 2", tier=2)

        total = memory.count_total()
        assert total == 2

    def test_get_stats(self, memory):
        """Test getting memory statistics."""
        memory.store(content="Fact", tier=1, domain="research")
        memory.store(content="Summary", tier=2, domain="music")

        stats = memory.get_stats()
        assert "total_entries" in stats
        assert "by_tier" in stats
        assert "by_domain" in stats
        assert stats["total_entries"] == 2

    def test_retrieve_limit(self, memory):
        """Test retrieve with limit."""
        for i in range(10):
            memory.store(content=f"Entry {i}", tier=1)

        limited = memory.retrieve_by_tier(1, limit=3)
        assert len(limited) == 3

    def test_update_entry(self, memory):
        """Test updating an existing entry."""
        memory_id = memory.store(content="Original", tier=1)
        memory.store(content="Updated", tier=2, memory_id=memory_id)

        entry = memory.get_by_id(memory_id)
        assert entry["content"] == "Updated"
        assert entry["tier"] == 2
