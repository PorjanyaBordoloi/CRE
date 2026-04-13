"""API key validation for the CRE API."""

import os
import secrets
from fastapi import Header, HTTPException, status


def get_api_keys() -> set:
    """Load valid API keys from environment variable (comma-separated)."""
    raw = os.getenv("API_KEYS", "")
    return set(k.strip() for k in raw.split(",") if k.strip())


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI dependency: validate X-API-Key header against API_KEYS env var."""
    valid_keys = get_api_keys()
    if not valid_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key store not configured on server.",
        )
    if x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return x_api_key


def generate_api_key() -> str:
    """Utility to generate a new API key. Use in admin scripts."""
    return secrets.token_urlsafe(32)
