"""GET /v1/status — workspace statistics for the authenticated user."""

import hashlib
from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.workspace import get_workspace_path, build_vector_store, build_memory
from api.models.schemas import StatusResponse

router = APIRouter()


@router.get("/status", response_model=StatusResponse)
async def get_status(api_key: str = Depends(verify_api_key)):
    workspace = get_workspace_path(api_key)
    workspace_id = hashlib.sha256(api_key.encode()).hexdigest()[:8]

    vs = build_vector_store(workspace)
    mem = build_memory(workspace)

    vs_count = vs.count()
    tier_counts = mem.count_by_tier()  # returns {1: n, 2: n, 3: n}

    t1 = tier_counts.get(1, 0)
    t2 = tier_counts.get(2, 0)
    t3 = tier_counts.get(3, 0)

    return StatusResponse(
        workspace_id=workspace_id,
        vector_store_count=vs_count,
        memory_tier1_count=t1,
        memory_tier2_count=t2,
        memory_tier3_count=t3,
        total_chunks=vs_count + t1 + t2 + t3,
    )
