"""L3: Pluggable sidecar LLM backends (Anthropic, OpenAI, Ollama)."""

import os
import json
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime


class SidecarBackend(ABC):
    """Abstract base class for sidecar LLM backends."""

    def __init__(self, api_key_env: str, model: str):
        """Initialize sidecar backend.

        Args:
            api_key_env: Environment variable name for API key
            model: Model name/identifier
        """
        self.api_key = os.getenv(api_key_env)
        self.model = model
        self.token_log_path = Path.cwd() / ".cre" / "token_log.jsonl"
        self.token_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_tokens(self, task: str, input_tokens: int, output_tokens: int) -> None:
        """Log token usage to .cre/token_log.jsonl."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "task": task,
            "model": self.model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        }
        with open(self.token_log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @abstractmethod
    def compress(self, text: str) -> str:
        """Compress/summarize text using the sidecar LLM.

        Args:
            text: Raw text to compress

        Returns:
            Compressed summary
        """
        pass

    @abstractmethod
    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query.

        Args:
            query: Query string
            chunks: List of chunk texts

        Returns:
            Ranked chunk texts (best first)
        """
        pass


class AnthropicSidecar(SidecarBackend):
    """Sidecar backend using Anthropic Claude."""

    def __init__(self, api_key_env: str = "ANTHROPIC_API_KEY", model: str = "claude-haiku-4-5"):
        """Initialize Anthropic sidecar.

        Args:
            api_key_env: Environment variable for API key
            model: Claude model name
        """
        super().__init__(api_key_env, model)
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=self.api_key)
        except ImportError:
            raise ImportError("anthropic package not installed")

    def compress(self, text: str) -> str:
        """Compress text using Claude."""
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        prompt = f"""Compress this text into a concise summary, preserving key facts and decisions:

{text}

Return only the compressed summary, no preamble."""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        output = message.content[0].text
        self._log_tokens(
            "compress",
            message.usage.input_tokens,
            message.usage.output_tokens,
        )
        return output

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        prompt = f"""Rank these chunks by relevance to the query (most relevant first).
Return only the chunk indices in order, comma-separated.

Query: {query}

Chunks:
{chunks_str}"""

        message = self.client.messages.create(
            model=self.model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )

        output = message.content[0].text
        self._log_tokens(
            "rank",
            message.usage.input_tokens,
            message.usage.output_tokens,
        )

        try:
            indices = [int(x.strip()) for x in output.split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class OpenAISidecar(SidecarBackend):
    """Sidecar backend using OpenAI GPT."""

    def __init__(self, api_key_env: str = "OPENAI_API_KEY", model: str = "gpt-4o-mini"):
        """Initialize OpenAI sidecar.

        Args:
            api_key_env: Environment variable for API key
            model: OpenAI model name
        """
        super().__init__(api_key_env, model)
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("openai package not installed")

    def compress(self, text: str) -> str:
        """Compress text using GPT."""
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": f"""Compress this text into a concise summary:

{text}

Return only the summary.""",
                }
            ],
        )

        output = response.choices[0].message.content
        self._log_tokens(
            "compress",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return output

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=128,
            messages=[
                {
                    "role": "user",
                    "content": f"""Rank by relevance to query. Return indices only, comma-separated.

Query: {query}

{chunks_str}""",
                }
            ],
        )

        output = response.choices[0].message.content
        self._log_tokens(
            "rank",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )

        try:
            indices = [int(x.strip()) for x in output.split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class OllamaSidecar(SidecarBackend):
    """Sidecar backend using Ollama (local models)."""

    def __init__(self, api_key_env: str = "", model: str = "mistral"):
        """Initialize Ollama sidecar.

        Args:
            api_key_env: Not used (Ollama is local)
            model: Ollama model name
        """
        super().__init__(api_key_env or "OLLAMA_BASE_URL", model)
        try:
            import ollama
            self.client = ollama
        except ImportError:
            raise ImportError("ollama package not installed")

    def compress(self, text: str) -> str:
        """Compress text using Ollama."""
        response = self.client.generate(
            model=self.model,
            prompt=f"Compress this text concisely:\n\n{text}",
            stream=False,
        )
        return response["response"]

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        response = self.client.generate(
            model=self.model,
            prompt=f"""Rank by relevance (indices only, comma-separated):

Query: {query}

{chunks_str}""",
            stream=False,
        )

        try:
            indices = [int(x.strip()) for x in response["response"].split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class GroqSidecar(SidecarBackend):
    """Sidecar backend using Groq (free, ultra-fast inference)."""

    def __init__(self, api_key_env: str = "GROQ_API_KEY", model: str = "mixtral-8x7b-32768"):
        """Initialize Groq sidecar.

        Args:
            api_key_env: Environment variable for API key
            model: Groq model name
        """
        super().__init__(api_key_env, model)
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            raise ImportError("groq package not installed. Install with: pip install groq")

    def compress(self, text: str) -> str:
        """Compress text using Groq."""
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        prompt = f"""Compress this text into a concise summary, preserving key facts and decisions:

{text}

Return only the compressed summary, no preamble."""

        message = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        output = message.choices[0].message.content
        self._log_tokens(
            "compress",
            message.usage.prompt_tokens,
            message.usage.completion_tokens,
        )
        return output

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        prompt = f"""Rank these chunks by relevance to the query (most relevant first).
Return only the chunk indices in order, comma-separated.

Query: {query}

Chunks:
{chunks_str}"""

        message = self.client.chat.completions.create(
            model=self.model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )

        output = message.choices[0].message.content
        self._log_tokens(
            "rank",
            message.usage.prompt_tokens,
            message.usage.completion_tokens,
        )

        try:
            indices = [int(x.strip()) for x in output.split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class GeminiSidecar(SidecarBackend):
    """Sidecar backend using Google Gemini (reasoning-focused)."""

    def __init__(self, api_key_env: str = "GOOGLE_API_KEY", model: str = "gemini-2.0-flash"):
        """Initialize Gemini sidecar.

        Args:
            api_key_env: Environment variable for API key
            model: Google Gemini model name
        """
        super().__init__(api_key_env, model)
        try:
            import google.generativeai as genai
            if self.api_key:
                genai.configure(api_key=self.api_key)
            self.client = genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Install with: pip install google-generativeai")

    def compress(self, text: str) -> str:
        """Compress text using Gemini."""
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        prompt = f"""Compress this text into a concise summary, preserving key facts and decisions:

{text}

Return only the compressed summary, no preamble."""

        model = self.client.GenerativeModel(self.model)
        response = model.generate_content(prompt)

        # Estimate tokens (Gemini doesn't always return token counts)
        input_tokens = len(text.split()) * 1.3
        output_tokens = len(response.text.split()) * 1.3
        self._log_tokens("compress", int(input_tokens), int(output_tokens))

        return response.text

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        prompt = f"""Rank these chunks by relevance to the query (most relevant first).
Return only the chunk indices in order, comma-separated.

Query: {query}

Chunks:
{chunks_str}"""

        model = self.client.GenerativeModel(self.model)
        response = model.generate_content(prompt)

        input_tokens = len(prompt.split()) * 1.3
        output_tokens = len(response.text.split()) * 1.3
        self._log_tokens("rank", int(input_tokens), int(output_tokens))

        try:
            indices = [int(x.strip()) for x in response.text.split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class OpenRouterSidecar(SidecarBackend):
    """Sidecar backend using OpenRouter (gateway to 100+ models)."""

    def __init__(self, api_key_env: str = "OPENROUTER_API_KEY", model: str = "mistralai/mistral-7b-instruct"):
        """Initialize OpenRouter sidecar.

        Args:
            api_key_env: Environment variable for API key
            model: OpenRouter model slug
        """
        super().__init__(api_key_env, model)
        try:
            from openai import OpenAI
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://openrouter.io/api/v1",
            )
        except ImportError:
            raise ImportError("openai package not installed (required for OpenRouter). Install with: pip install openai")

    def compress(self, text: str) -> str:
        """Compress text using OpenRouter."""
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        prompt = f"""Compress this text into a concise summary, preserving key facts and decisions:

{text}

Return only the compressed summary, no preamble."""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        output = response.choices[0].message.content
        self._log_tokens(
            "compress",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )
        return output

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Rank chunks by relevance to query."""
        if not chunks:
            return []
        if not self.api_key:
            raise ValueError(f"API key not found in {self.api_key_env} environment variable")

        chunks_str = "\n---\n".join(f"Chunk {i}:\n{c}" for i, c in enumerate(chunks))
        prompt = f"""Rank these chunks by relevance to the query (most relevant first).
Return only the chunk indices in order, comma-separated.

Query: {query}

Chunks:
{chunks_str}"""

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=128,
            messages=[{"role": "user", "content": prompt}],
        )

        output = response.choices[0].message.content
        self._log_tokens(
            "rank",
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
        )

        try:
            indices = [int(x.strip()) for x in output.split(",")]
            return [chunks[i] for i in indices if i < len(chunks)]
        except (ValueError, IndexError):
            return chunks


class NoOpSidecar(SidecarBackend):
    """No-op sidecar for L1+L2 only mode (no compression)."""

    def __init__(self):
        """Initialize no-op sidecar."""
        super().__init__("", "none")

    def compress(self, text: str) -> str:
        """Return text unchanged."""
        return text

    def rank(self, query: str, chunks: List[str]) -> List[str]:
        """Return chunks unchanged."""
        return chunks


def get_sidecar(config) -> SidecarBackend:
    """Factory function to get configured sidecar backend.

    Args:
        config: Config object with sidecar settings

    Returns:
        Sidecar backend instance

    Supported backends:
        - anthropic: Claude (Haiku recommended for cost)
        - openai: GPT-4o-mini
        - groq: Mixtral (ultra-fast, free tier available)
        - gemini: Google Gemini (reasoning-focused)
        - openrouter: 100+ models (pick any)
        - ollama: Local models (Mistral, Phi-3, etc.)
        - none: L1+L2 only (no sidecar)
    """
    backend = config.sidecar_backend.lower()

    if backend == "anthropic":
        return AnthropicSidecar(config.sidecar_api_key_env, config.sidecar_model)
    elif backend == "openai":
        return OpenAISidecar(config.sidecar_api_key_env, config.sidecar_model)
    elif backend == "groq":
        return GroqSidecar(config.sidecar_api_key_env, config.sidecar_model)
    elif backend == "gemini":
        return GeminiSidecar(config.sidecar_api_key_env, config.sidecar_model)
    elif backend == "openrouter":
        return OpenRouterSidecar(config.sidecar_api_key_env, config.sidecar_model)
    elif backend == "ollama":
        return OllamaSidecar(model=config.sidecar_model)
    elif backend == "none":
        return NoOpSidecar()
    else:
        raise ValueError(f"Unknown sidecar backend: {backend}. Supported: anthropic, openai, groq, gemini, openrouter, ollama, none")
