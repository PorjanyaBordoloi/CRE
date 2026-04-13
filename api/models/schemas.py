"""Pydantic request/response schemas for the CRE API."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List, Any, Dict


# --- Ingest ---
class IngestRequest(BaseModel):
    content: str = Field(..., description="Text content to ingest into CRE")
    domain: Optional[str] = Field("general", description="Domain label (e.g. research, self, project)")
    tier: Optional[int] = Field(1, ge=1, le=3, description="Initial memory tier (1=raw, 2=summary, 3=theme)")


class IngestResponse(BaseModel):
    status: str
    chunks_ingested: int
    domain: str
    tier: int


# --- Retrieve ---
class RetrieveRequest(BaseModel):
    query: str = Field(..., description="Natural language query to retrieve context for")
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Number of results to return")


class RetrieveResponse(BaseModel):
    query: str
    results: List[Any]
    token_estimate: int


# --- Inject ---
class InjectRequest(BaseModel):
    query: str = Field(..., description="Query to retrieve and format for prompt injection")
    budget: Optional[int] = Field(2000, ge=100, le=8000, description="Token budget for injected context")
    format: Optional[Literal["markdown", "plain", "json"]] = Field(
        "markdown", description="Output format"
    )


class InjectResponse(BaseModel):
    query: str
    injected_context: str
    token_count: int
    budget: int
    format: str


# --- Compress ---
class CompressRequest(BaseModel):
    content: str = Field(..., description="Session log or document text to compress")
    target_tier: Optional[int] = Field(2, ge=2, le=3, description="Target compression tier")


class CompressResponse(BaseModel):
    status: str
    original_length: int
    compressed_length: int
    target_tier: int
    summary: str


# --- Status ---
class StatusResponse(BaseModel):
    workspace_id: str
    vector_store_count: int
    memory_tier1_count: int
    memory_tier2_count: int
    memory_tier3_count: int
    total_chunks: int
