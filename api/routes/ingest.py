"""POST /v1/ingest — ingest text content into a user's CRE workspace."""

import os
import tempfile
from pathlib import Path
from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.workspace import get_workspace_path, build_vector_store, build_memory, build_config
from api.sidecar_resolver import resolve_sidecar
from api.models.schemas import IngestRequest, IngestResponse

from cre.ingestor import Ingestor
from cre.sidecar import SidecarBackend

router = APIRouter()


@router.post("/ingest", response_model=IngestResponse)
async def ingest_content(
    request: IngestRequest,
    api_key: str = Depends(verify_api_key),
    sidecar: SidecarBackend = Depends(resolve_sidecar),
):
    workspace = get_workspace_path(api_key)
    vs = build_vector_store(workspace)
    mem = build_memory(workspace)
    ingestor = Ingestor(vector_store=vs, memory=mem, sidecar=sidecar)

    # Write content to a temp file then ingest; Ingestor expects a file path
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(request.content)
        temp_path = f.name

    try:
        result = ingestor.ingest_file(
            Path(temp_path),
            domain=request.domain,
            tier=request.tier,
        )
        chunks = len(result) if isinstance(result, list) else 0
    finally:
        os.unlink(temp_path)

    return IngestResponse(
        status="ok",
        chunks_ingested=chunks,
        domain=request.domain,
        tier=request.tier,
    )
