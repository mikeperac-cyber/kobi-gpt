from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.routers import admin, auth, health

UPLOADS = Path(__file__).resolve().parents[2] / "uploads"


def create_app() -> FastAPI:
    app = FastAPI(title="KOBI-GPT")
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
