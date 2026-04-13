"""POST /v1/inject — retrieve and format context ready for prompt injection."""

from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.workspace import get_workspace_path, build_vector_store, build_memory, build_config
from api.sidecar_resolver import resolve_sidecar
from api.models.schemas import InjectRequest, InjectResponse

from cre.retriever import Retriever
from cre.injector import Injector
from cre.sidecar import SidecarBackend

router = APIRouter()


@router.post("/inject", response_model=InjectResponse)
async def inject_context(
    request: InjectRequest,
    api_key: str = Depends(verify_api_key),
    sidecar: SidecarBackend = Depends(resolve_sidecar),
):
    workspace = get_workspace_path(api_key)
    config = build_config(workspace)
    vs = build_vector_store(workspace)
    mem = build_memory(workspace)
    retriever = Retriever(vector_store=vs, memory=mem, sidecar=sidecar, config=config)

    bundle = retriever.retrieve(request.query, token_budget=request.budget)
    context_block = Injector.inject(bundle, format=request.format)
    token_count = len(context_block) // 4

    return InjectResponse(
        query=request.query,
        injected_context=context_block,
        token_count=token_count,
        budget=request.budget,
        format=request.format,
    )
