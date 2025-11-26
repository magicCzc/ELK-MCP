"""
Copyright (c) 2025, elk-MCP Project.
All rights reserved.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routes.logs import router as logs_router
from .routes.health import router as health_router
from .routes.indices import router as indices_router
from .metrics.metrics import metrics_app
from .indexes.service import index_discovery


def create_app() -> FastAPI:
    app = FastAPI(title="elk-mcp", version="0.1.0")

    # CORS for Dify integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router, tags=["health"])
    app.include_router(logs_router, prefix="/api/logs", tags=["logs"])
    app.include_router(indices_router, prefix="/api/indices", tags=["indices"])

    if settings.METRICS_ENABLED:
        app.mount("/metrics", metrics_app)

    @app.on_event("startup")
    def _startup():
        index_discovery.startup()

    @app.on_event("shutdown")
    def _shutdown():
        index_discovery.shutdown()

    return app


app = create_app()
