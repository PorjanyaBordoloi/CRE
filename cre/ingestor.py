"""File ingestion: reading, chunking, and embedding markdown files."""

import re
from pathlib import Path
from typing import List, Optional, Tuple
import uuid
import tiktoken


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

    def __init__(self, vector_store, memory, chunker: Optional[Chunker] = None):
        """Initialize ingestor.

        Args:
            vector_store: VectorStore instance
            memory: Memory instance
            chunker: Chunker instance (uses defaults if not provided)
        """
        self.vector_store = vector_store
        self.memory = memory
        self.chunker = chunker or Chunker()

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
