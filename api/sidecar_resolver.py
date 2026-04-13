"""Sidecar resolver — Option C: server default + per-request override.

Priority:
  1. Per-request headers (X-Sidecar-Backend + X-Sidecar-API-Key)
  2. Server default (CRE_DEFAULT_SIDECAR_BACKEND env var, defaults to groq)
  3. Falls back to NoOpSidecar if no API key is available

Server default is Groq — works out of the box with zero extra headers.
Any caller can override backend and key per-request.

Note: per-request key injection uses a temporary os.environ mutation.
This is acceptable for a single-process v0.1 demo deployment. For
multi-threaded production use, replace with a thread-local or per-request
config object pattern.
"""

import os
from contextlib import contextmanager
from typing import Optional
from fastapi import Header

from cre.sidecar import (
    SidecarBackend,
    AnthropicSidecar,
    OpenAISidecar,
    GroqSidecar,
    GeminiSidecar,
    OllamaSidecar,
    NoOpSidecar,
)

try:
    from cre.sidecar import OpenRouterSidecar
    _HAS_OPENROUTER = True
except ImportError:
    _HAS_OPENROUTER = False


DEFAULT_BACKEND = os.getenv("CRE_DEFAULT_SIDECAR_BACKEND", "groq")

_MODEL_MAP: dict = {
    "groq":        "mixtral-8x7b-32768",
    "anthropic":   "claude-haiku-4-5",
    "openai":      "gpt-4o-mini",
    "gemini":      "gemini-2.0-flash",
    "openrouter":  "mistralai/mistral-7b-instruct",
    "ollama":      "mistral",
    "none":        None,
}

_KEY_ENV_MAP: dict = {
    "groq":       "GROQ_API_KEY",
    "anthropic":  "ANTHROPIC_API_KEY",
    "openai":     "OPENAI_API_KEY",
    "gemini":     "GOOGLE_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "ollama":     "",
    "none":       "",
}


@contextmanager
def _temp_env(key: str, value: str):
    """Temporarily set an env var for the duration of sidecar __init__."""
    old = os.environ.get(key)
    os.environ[key] = value
    try:
        yield
    finally:
        if old is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = old


def _build_sidecar(backend: str, api_key: str) -> SidecarBackend:
    """Instantiate the correct SidecarBackend."""
    model = _MODEL_MAP.get(backend, _MODEL_MAP[DEFAULT_BACKEND])
    key_env = _KEY_ENV_MAP.get(backend, "")

    if backend == "ollama":
        return OllamaSidecar(model=model)
    if backend == "none" or not model:
        return NoOpSidecar()

    # Temporarily inject the per-request key into env so the sidecar __init__
    # picks it up via os.getenv(). Reverts immediately after construction.
    ctx = _temp_env(key_env, api_key) if (api_key and key_env) else _noop_ctx()

    with ctx:
        if backend == "anthropic":
            return AnthropicSidecar(api_key_env=key_env, model=model)
        elif backend == "openai":
            return OpenAISidecar(api_key_env=key_env, model=model)
        elif backend == "groq":
            return GroqSidecar(api_key_env=key_env, model=model)
        elif backend == "gemini":
            return GeminiSidecar(api_key_env=key_env, model=model)
        elif backend == "openrouter" and _HAS_OPENROUTER:
            return OpenRouterSidecar(api_key_env=key_env, model=model)
        else:
            return NoOpSidecar()


@contextmanager
def _noop_ctx():
    yield


def resolve_sidecar(
    x_sidecar_backend: Optional[str] = Header(None, alias="X-Sidecar-Backend"),
    x_sidecar_api_key: Optional[str] = Header(None, alias="X-Sidecar-API-Key"),
) -> SidecarBackend:
    """FastAPI dependency: resolve which sidecar to use for this request.

    Caller patterns:
      1. No headers → uses server Groq default (zero friction for Sarvam AI demo)
      2. X-Sidecar-Backend + X-Sidecar-API-Key → caller brings their own key
      3. X-Sidecar-Backend: ollama → local model, no key needed
    """
    backend = (x_sidecar_backend or DEFAULT_BACKEND).lower().strip()

    # Resolve API key: prefer per-request header, fall back to server env var
    if x_sidecar_api_key:
        api_key = x_sidecar_api_key
    else:
        key_env = _KEY_ENV_MAP.get(backend, "")
        api_key = os.getenv(key_env, "") if key_env else ""

    # Graceful fallback: if no key and backend requires one → NoOpSidecar
    if not api_key and backend not in ("ollama", "none"):
        return NoOpSidecar()

    return _build_sidecar(backend, api_key)
