"""L2: SQLite tiered memory system (raw facts, summaries, themes)."""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


class Memory:
    """SQLite-backed tiered memory: raw facts (T1), summaries (T2), themes (T3)."""

    TIERS = {
        1: "raw",  # Verbatim facts, decisions, code snippets
        2: "summary",  # LLM-compressed summaries (paragraph-level)
        3: "theme",  # High-level themes (bullet-level)
    }

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize SQLite tiered memory.

        Args:
            db_path: Path to memory.db. Defaults to .cre/memory.db
        """
        self.db_path = db_path or Path.cwd() / ".cre" / "memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _init_schema(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    tier INTEGER NOT NULL,
                    domain TEXT,
                    source_file TEXT,
                    token_count INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    tags TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_tier ON memory(tier)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_domain ON memory(domain)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_source ON memory(source_file)"
            )
            conn.commit()

    def store(
        self,
        content: str,
        tier: int,
        domain: str = "",
        source_file: str = "",
        token_count: int = 0,
        tags: Optional[List[str]] = None,
        memory_id: Optional[str] = None,
    ) -> str:
        """Store a memory entry.

        Args:
            content: Memory content
            tier: Tier level (1=raw, 2=summary, 3=theme)
            domain: Domain classification
            source_file: Source file path
            token_count: Estimated token count
            tags: List of tags (stored as JSON)
            memory_id: Custom ID; auto-generated if not provided

        Returns:
            Memory ID
        """
        memory_id = memory_id or str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO memory
                (id, content, tier, domain, source_file, token_count, created_at, updated_at, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    memory_id,
                    content,
                    tier,
                    domain,
                    source_file,
                    token_count,
                    now,
                    now,
                    json.dumps(tags or []),
                ),
            )
            conn.commit()

        return memory_id

    def retrieve_by_tier(self, tier: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve memories by tier.

        Args:
            tier: Tier level (1, 2, or 3)
            limit: Maximum results

        Returns:
            List of memory entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memory WHERE tier = ? ORDER BY updated_at DESC LIMIT ?",
                (tier, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def retrieve_by_domain(
        self, domain: str, tier: Optional[int] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Retrieve memories by domain, optionally filtered by tier.

        Args:
            domain: Domain name
            tier: Optional tier filter
            limit: Maximum results

        Returns:
            List of memory entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if tier is not None:
                rows = conn.execute(
                    "SELECT * FROM memory WHERE domain = ? AND tier = ? ORDER BY updated_at DESC LIMIT ?",
                    (domain, tier, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM memory WHERE domain = ? ORDER BY updated_at DESC LIMIT ?",
                    (domain, limit),
                ).fetchall()
            return [dict(row) for row in rows]

    def retrieve_all(self, limit: int = 1000) -> List[Dict[str, Any]]:
        """Retrieve all memories, ordered by update time.

        Args:
            limit: Maximum results

        Returns:
            List of memory entries
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM memory ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_by_id(self, memory_id: str) -> Optional[Dict[str, Any]]:
        """Get a single memory by ID.

        Args:
            memory_id: Memory ID

        Returns:
            Memory entry or None if not found
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM memory WHERE id = ?",
                (memory_id,),
            ).fetchone()
            return dict(row) if row else None

    def delete(self, memory_id: str) -> None:
        """Delete a memory entry by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM memory WHERE id = ?", (memory_id,))
            conn.commit()

    def count_by_tier(self) -> Dict[int, int]:
        """Get count of memories per tier."""
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT tier, COUNT(*) as count FROM memory GROUP BY tier"
            ).fetchall()
            return {tier: count for tier, count in rows}

    def count_total(self) -> int:
        """Get total memory count."""
        with sqlite3.connect(self.db_path) as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM memory"
            ).fetchone()[0]
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM memory"
            ).fetchone()[0]
            by_tier = conn.execute(
                "SELECT tier, COUNT(*) FROM memory GROUP BY tier"
            ).fetchall()
            by_domain = conn.execute(
                "SELECT domain, COUNT(*) FROM memory WHERE domain != '' GROUP BY domain"
            ).fetchall()

        return {
            "total_entries": total,
            "by_tier": {tier: count for tier, count in by_tier},
            "by_domain": {domain: count for domain, count in by_domain},
            "db_path": str(self.db_path),
        }
