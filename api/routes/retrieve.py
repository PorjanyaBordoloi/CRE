"""POST /v1/retrieve — retrieve context chunks for a query."""

from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.workspace import get_workspace_path, build_vector_store, build_memory, build_config
from api.sidecar_resolver import resolve_sidecar
from api.models.schemas import RetrieveRequest, RetrieveResponse

from cre.retriever import Retriever
from cre.sidecar import SidecarBackend

router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_context(
    request: RetrieveRequest,
    api_key: str = Depends(verify_api_key),
    sidecar: SidecarBackend = Depends(resolve_sidecar),
):
    workspace = get_workspace_path(api_key)
    config = build_config(workspace)
    vs = build_vector_store(workspace)
    mem = build_memory(workspace)
    retriever = Retriever(vector_store=vs, memory=mem, sidecar=sidecar, config=config)

    bundle = retriever.retrieve(request.query, top_k=request.top_k)

    # Flatten all context items into a results list
    results = bundle.themes + bundle.summaries + bundle.facts + bundle.raw_chunks

    # Rough token estimate: 1 token ≈ 4 chars
    token_estimate = sum(len(str(r)) for r in results) // 4

    return RetrieveResponse(
        query=request.query,
        results=results,
        token_estimate=token_estimate,
    )
