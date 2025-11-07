from __future__ import annotations

from fastapi import FastAPI

from .routes import router


def create_app() -> FastAPI:
    app = FastAPI(
        title="FIT File CustomGPT Action",
        version="0.1.0",
        summary="Expose FIT parsing and generation via a lightweight FastAPI service.",
    )
    app.include_router(router, prefix="/fit")
    return app


app = create_app()
