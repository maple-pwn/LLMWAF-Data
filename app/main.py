from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api import api_router
from core.bootstrap import bootstrap_defaults
from core.database import init_database
from core.errors import AppError
from core.logging import configure_logging


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    init_database()
    bootstrap_defaults()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Sample Factory", version="0.1.0", lifespan=lifespan)
    app.include_router(api_router)

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "errors": exc.errors},
        )

    return app


app = create_app()
