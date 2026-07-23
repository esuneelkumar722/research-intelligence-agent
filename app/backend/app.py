
from __future__ import annotations

import asyncio
import logging
import pathlib
import sys
import uuid

# Set here (not just main.py) so uvicorn worker processes also get the right policy
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.responses import FileResponse, JSONResponse

from app.backend.api.health import router as health_router
from app.backend.api.research import router as research_router
from app.backend.core.azure_clients import lifespan
from app.backend.core.config import get_settings
from app.backend.core.rate_limiter import limiter
from app.backend.core.telemetry import setup_telemetry

_FRONTEND_DIST = pathlib.Path(__file__).parent.parent / "frontend" / "dist"

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()

    setup_telemetry()

    app = FastAPI(
        title="Research Intelligence Agent",
        description="Production-grade Multi-Agent Research Platform — LangGraph + LangChain on Azure",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    app.include_router(health_router)
    app.include_router(research_router, prefix="/v1")

    # In dev Vite serves the frontend on :5173; in production the built dist/
    # is embedded in the Docker image and served here (SPA fallback to index.html)
    if _FRONTEND_DIST.is_dir():
        app.mount(
            "/assets",
            StaticFiles(directory=_FRONTEND_DIST / "assets"),
            name="assets",
        )

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(_: Request, full_path: str) -> FileResponse:
            index = _FRONTEND_DIST / "index.html"
            return FileResponse(index)

    return app


def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": f"Rate limit exceeded. Retry after {exc.retry_after}s."},
    )
