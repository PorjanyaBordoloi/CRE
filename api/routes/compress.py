"""POST /v1/compress — compress content and store in tiered memory.

Note: Memory class has no .compress() method, so compression is performed
directly via the resolved sidecar, and the result is stored via Memory.store().
This is the adapter layer described in CLAUDE_API.md §Important Notes #3.
"""

from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.workspace import get_workspace_path, build_memory
from api.sidecar_resolver import resolve_sidecar
from api.models.schemas import CompressRequest, CompressResponse

from cre.sidecar import SidecarBackend, NoOpSidecar

router = APIRouter()


@router.post("/compress", response_model=CompressResponse)
async def compress_content(
    request: CompressRequest,
    api_key: str = Depends(verify_api_key),
    sidecar: SidecarBackend = Depends(resolve_sidecar),
):
    workspace = get_workspace_path(api_key)
    mem = build_memory(workspace)

    # Compress via sidecar; fall back to truncation if NoOpSidecar
    if isinstance(sidecar, NoOpSidecar):
        # No LLM available: store raw content as-is
        summary = request.content[:2000]
    else:
        summary = sidecar.compress(request.content)

    mem.store(
        content=summary,
        tier=request.target_tier,
        domain="compressed",
        source_file="api/compress",
        token_count=len(summary) // 4,
    )

    return CompressResponse(
        status="ok",
        original_length=len(request.content),
        compressed_length=len(summary),
        target_tier=request.target_tier,
        summary=summary,
    )
