"""File ingestion: reading, chunking, and embedding markdown files."""

import re
import json
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any
import uuid
import tiktoken
from datetime import datetime


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count tokens in text using tiktoken."""
    encoding = tiktoken.get_encoding(encoding_name)
    return len(encoding.encode(text))


class Chunker:
    """Sliding window text chunker for markdown files."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 64):
        """Initialize chunker.

        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Overlap between chunks in tokens
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, text: str) -> List[Tuple[str, int]]:
        """Split text into overlapping chunks.

        Args:
            text: Text to chunk

        Returns:
            List of (chunk_text, token_count) tuples
        """
        # Split by paragraphs first
        paragraphs = text.split("\n\n")

        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = count_tokens(para)

            # If single paragraph exceeds chunk_size, split it
            if para_tokens > self.chunk_size:
                # Flush current chunk if it has content
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append((chunk_text, current_tokens))
                    # Start new chunk with overlap
                    current_chunk = current_chunk[-max(1, len(current_chunk) // 2):]
                    current_tokens = sum(count_tokens(p) for p in current_chunk)

                # Split paragraph into sentences
                sentences = re.split(r"(?<=[.!?])\s+", para)
                para_chunk = []
                para_chunk_tokens = 0

                for sent in sentences:
                    sent_tokens = count_tokens(sent)
                    if para_chunk_tokens + sent_tokens > self.chunk_size:
                        if para_chunk:
                            chunk_text = " ".join(para_chunk)
                            chunks.append((chunk_text, para_chunk_tokens))
                        para_chunk = [sent]
                        para_chunk_tokens = sent_tokens
                    else:
                        para_chunk.append(sent)
                        para_chunk_tokens += sent_tokens

                if para_chunk:
                    chunk_text = " ".join(para_chunk)
                    chunks.append((chunk_text, para_chunk_tokens))
            else:
                # Add paragraph to current chunk
                if current_tokens + para_tokens > self.chunk_size and current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunks.append((chunk_text, current_tokens))
                    # Overlap: keep last paragraph(s)
                    current_chunk = current_chunk[-max(1, len(current_chunk) // 2):]
                    current_tokens = sum(count_tokens(p) for p in current_chunk)

                current_chunk.append(para)
                current_tokens += para_tokens

        # Flush remaining chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunks.append((chunk_text, current_tokens))

        return chunks


class Ingestor:
    """Ingest markdown files and populate vector store + memory."""

    def __init__(self, vector_store, memory, sidecar=None, chunker: Optional[Chunker] = None):
        """Initialize ingestor.

        Args:
            vector_store: VectorStore instance
            memory: Memory instance
            sidecar: SidecarBackend instance (optional, for compression)
            chunker: Chunker instance (uses defaults if not provided)
        """
        self.vector_store = vector_store
        self.memory = memory
        self.sidecar = sidecar
        self.chunker = chunker or Chunker()
        self.token_log_path = Path.cwd() / ".cre" / "token_log.jsonl"

    def _log_compression(
        self,
        operation: str,
        source_file: str,
        domain: str,
        input_tokens: int,
        output_tokens: int,
    ) -> None:
        """Log compression token usage to .cre/token_log.jsonl."""
        self.token_log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "source_file": source_file,
            "domain": domain,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
        with open(self.token_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def compress_source(
        self,
        source_file: str,
        domain: str,
        force: bool = False,
    ) -> Dict[str, Any]:
        """Compress all T1 entries for a source_file into T2 and T3.

        Args:
            source_file: Source file path
            domain: Domain classification
            force: Overwrite existing T2/T3 (default False)

        Returns:
            Dict with tier2_id, tier3_id, input_tokens, output_tokens_t2, output_tokens_t3
        """
        result = {
            "tier2_id": None,
            "tier3_id": None,
            "input_tokens": 0,
            "output_tokens_t2": 0,
            "output_tokens_t3": 0,
            "skipped": False,
            "reason": None,
        }

        # Check if sidecar is available
        if not self.sidecar or self.sidecar.__class__.__name__ == "NoOpSidecar":
            result["skipped"] = True
            result["reason"] = "Sidecar backend is 'none' (no LLM compression)"
            return result

        # Fetch all T1 entries for this source_file
        tier1_entries = self.memory.retrieve_by_domain(domain, tier=1)
        source_entries = [e for e in tier1_entries if e.get("source_file") == source_file]

        if not source_entries:
            result["skipped"] = True
            result["reason"] = "No T1 entries found for this source"
            return result

        # Check if T2/T3 already exist
        tier2_entries = self.memory.retrieve_by_domain(domain, tier=2)
        tier3_entries = self.memory.retrieve_by_domain(domain, tier=3)
        tier2_exists = any(e.get("source_file") == source_file for e in tier2_entries)
        tier3_exists = any(e.get("source_file") == source_file for e in tier3_entries)

        if (tier2_exists or tier3_exists) and not force:
            result["skipped"] = True
            result["reason"] = "T2/T3 already exist (use --force to overwrite)"
            return result

        # Combine all T1 content
        combined_content = "\n\n".join(e["content"] for e in source_entries)
        input_tokens = count_tokens(combined_content)
        result["input_tokens"] = input_tokens

        try:
            # Generate T2 (paragraph summary)
            t2_prompt = f"""Compress these facts into one dense paragraph (max 120 words).
Preserve all technical decisions, names, constraints, open issues.
Output only the paragraph.

Facts:
{combined_content}"""

            t2_compressed = self.sidecar.compress(t2_prompt)
            t2_tokens = count_tokens(t2_compressed)
            result["output_tokens_t2"] = t2_tokens

            # Generate T3 (one sentence)
            t3_prompt = f"""One sentence (max 25 words): what this system is, its critical
path, its most urgent open issue. Output only the sentence.

Summary:
{t2_compressed}"""

            t3_compressed = self.sidecar.compress(t3_prompt)
            t3_tokens = count_tokens(t3_compressed)
            result["output_tokens_t3"] = t3_tokens

            # Store T2 and T3
            t2_id = str(uuid.uuid4())
            t3_id = str(uuid.uuid4())

            self.memory.store(
                content=t2_compressed,
                tier=2,
                domain=domain,
                source_file=source_file,
                token_count=t2_tokens,
                memory_id=t2_id,
            )

            self.memory.store(
                content=t3_compressed,
                tier=3,
                domain=domain,
                source_file=source_file,
                token_count=t3_tokens,
                memory_id=t3_id,
            )

            result["tier2_id"] = t2_id
            result["tier3_id"] = t3_id

            # Log token usage
            self._log_compression(
                "compress_t2",
                source_file,
                domain,
                input_tokens,
                t2_tokens,
            )
            self._log_compression(
                "compress_t3",
                source_file,
                domain,
                t2_tokens,
                t3_tokens,
            )

        except Exception as e:
            result["skipped"] = True
            result["reason"] = f"Compression failed: {str(e)}"

        return result

    def ingest_file(
        self,
        file_path: Path,
        domain: str = "",
        tier: int = 1,
    ) -> List[str]:
        """Ingest a single markdown file.

        Args:
            file_path: Path to markdown file
            domain: Domain classification
            tier: Default memory tier

        Returns:
            List of chunk IDs created
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = self.chunker.chunk(text)
        chunk_ids = []

        for chunk_text, token_count in chunks:
            chunk_id = f"{file_path.stem}_{uuid.uuid4().hex[:8]}"

            # Add to vector store
            self.vector_store.add_chunk(
                chunk_id=chunk_id,
                text=chunk_text,
                source_file=str(file_path),
                domain=domain,
                tier_hint=tier,
            )

            # Add to memory
            self.memory.store(
                content=chunk_text,
                tier=tier,
                domain=domain,
                source_file=str(file_path),
                token_count=token_count,
                memory_id=chunk_id,
            )

            chunk_ids.append(chunk_id)

        return chunk_ids

    def ingest_directory(
        self,
        dir_path: Path,
        domain: str = "",
        tier: int = 1,
        recursive: bool = True,
    ) -> List[str]:
        """Ingest all markdown files in a directory.

        Args:
            dir_path: Path to directory
            domain: Domain classification
            tier: Default memory tier
            recursive: Recursively ingest subdirectories

        Returns:
            List of all chunk IDs created
        """
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")

        all_chunk_ids = []
        pattern = "**/*.md" if recursive else "*.md"

        for md_file in sorted(dir_path.glob(pattern)):
            try:
                chunk_ids = self.ingest_file(md_file, domain=domain, tier=tier)
                all_chunk_ids.extend(chunk_ids)
            except Exception as e:
                print(f"Error ingesting {md_file}: {e}")

        return all_chunk_ids
