"""CRE API — FastAPI entrypoint."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import ingest, retrieve, inject, compress, status

app = FastAPI(
    title="CRE API",
    description=(
        "Context Retrieval Engine — REST API layer. "
        "Never waste tokens on context management again."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router, prefix="/v1", tags=["Ingest"])
app.include_router(retrieve.router, prefix="/v1", tags=["Retrieve"])
app.include_router(inject.router, prefix="/v1", tags=["Inject"])
app.include_router(compress.router, prefix="/v1", tags=["Compress"])
app.include_router(status.router, prefix="/v1", tags=["Status"])


@app.get("/")
def root():
    return {
        "service": "CRE API",
        "version": "0.1.0",
        "docs": "/docs",
        "github": "https://github.com/PorjanyaBordoloi/CRE",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
