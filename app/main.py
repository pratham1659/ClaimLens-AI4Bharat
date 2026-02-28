from pathlib import Path

from fastapi import FastAPI

from app.api.v1.router import api_v1_router
from app.core.middleware import RequestContextMiddleware
from app.core.settings import get_settings
from app.db.init_db import init_db


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    app.add_middleware(RequestContextMiddleware)
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.on_event("startup")
    def on_startup() -> None:
        Path(settings.storage_dir).mkdir(parents=True, exist_ok=True)
        Path(settings.faiss_index_root).mkdir(parents=True, exist_ok=True)
        init_db()

    return app


app = create_app()
