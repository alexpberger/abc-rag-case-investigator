"""FastAPI application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.db import close_pool, init_pool

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_pool()
    except Exception:
        logger.warning(
            "Postgres is not reachable. Source documents can still be read from disk.",
            exc_info=True,
        )
    yield
    close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    docs = "/docs" if settings.expose_api_docs else None
    app = FastAPI(
        title="ABC RAG Case Investigator",
        lifespan=lifespan,
        docs_url=docs,
        redoc_url="/redoc" if settings.expose_api_docs else None,
        openapi_url="/openapi.json" if settings.expose_api_docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    app.include_router(router, prefix="/api")
    return app


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
app = create_app()
