from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.db import ensure_indexes, get_db
from app.routers import admin, auth, health

UPLOADS = Path(__file__).resolve().parents[2] / "uploads"


@asynccontextmanager
async def lifespan(_app):
    await ensure_indexes(get_db())
    yield


def create_app() -> FastAPI:
    s = get_settings()
    local = s.frontend_origin.startswith(("http://localhost", "http://127.0.0.1"))
    if s.jwt_secret == "dev-secret-change-me" and not local:
        raise RuntimeError("Refusing to start: set JWT_SECRET to a private value")
    app = FastAPI(title="KOBI-GPT", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    UPLOADS.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
    return app


app = create_app()
