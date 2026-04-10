"""Configuration management for CRE."""

import os
from pathlib import Path
from typing import Optional, Dict, Any
import yaml


DEFAULT_CONFIG = {
    "version": "0.1",
    "sidecar": {
        "backend": "anthropic",  # anthropic | openai | ollama | none
        "model": "claude-haiku-4-5",
        "api_key_env": "ANTHROPIC_API_KEY",
    },
    "embedding": {
        "model": "all-MiniLM-L6-v2",
        "chunk_size": 512,
        "chunk_overlap": 64,
    },
    "memory": {
        "default_inject_budget": 2000,
        "tier_weights": [0.5, 0.35, 0.15],  # themes, summaries, facts
    },
}


class Config:
    """Load and manage .cre/config.yaml configuration."""

    def __init__(self, cre_dir: Optional[Path] = None):
        """Initialize config loader.

        Args:
            cre_dir: Path to .cre directory. Defaults to ./.cre
        """
        self.cre_dir = cre_dir or Path.cwd() / ".cre"
        self.config_file = self.cre_dir / "config.yaml"
        self._config: Dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load configuration from file or use defaults."""
        if self.config_file.exists():
            with open(self.config_file, "r") as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._merge_with_defaults({})

    def save(self) -> None:
        """Save current configuration to file."""
        self.cre_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            yaml.dump(self._config, f, default_flow_style=False, sort_keys=False)

    def initialize(self) -> None:
        """Initialize config with defaults."""
        self._config = DEFAULT_CONFIG.copy()
        self.save()

    def get(self, key: str, default: Any = None) -> Any:
        """Get nested config value using dot notation (e.g., 'sidecar.backend')."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value: Any) -> None:
        """Set nested config value using dot notation."""
        keys = key.split(".")
        current = self._config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value

    def _merge_with_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively merge config with defaults."""
        result = DEFAULT_CONFIG.copy()
        for key, value in config.items():
            if isinstance(value, dict) and key in result:
                result[key] = {**result[key], **value}
            else:
                result[key] = value
        return result

    @property
    def sidecar_backend(self) -> str:
        """Get configured sidecar backend."""
        return self.get("sidecar.backend", "anthropic")

    @property
    def sidecar_model(self) -> str:
        """Get configured sidecar model."""
        return self.get("sidecar.model", "claude-haiku-4-5")

    @property
    def sidecar_api_key_env(self) -> str:
        """Get sidecar API key environment variable name."""
        return self.get("sidecar.api_key_env", "ANTHROPIC_API_KEY")

    @property
    def embedding_model(self) -> str:
        """Get embedding model name."""
        return self.get("embedding.model", "all-MiniLM-L6-v2")

    @property
    def chunk_size(self) -> int:
        """Get chunk size in tokens."""
        return self.get("embedding.chunk_size", 512)

    @property
    def chunk_overlap(self) -> int:
        """Get chunk overlap in tokens."""
        return self.get("embedding.chunk_overlap", 64)

    @property
    def default_inject_budget(self) -> int:
        """Get default token budget for inject."""
        return self.get("memory.default_inject_budget", 2000)

    @property
    def tier_weights(self) -> list:
        """Get tier weights [themes, summaries, facts]."""
        return self.get("memory.tier_weights", [0.5, 0.35, 0.15])
