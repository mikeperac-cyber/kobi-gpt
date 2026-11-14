import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import get_settings
from app.core.db import ensure_indexes, get_db
from app.routers import admin, admin_kb, auth, company, compliance, dashboard, health, jobs, products, public, storefronts, uploads

KNOWN_CODES = {"password_too_long", "invalid_city", "invalid_certification", "photo_required"}


async def validation_handler(_req: Request, exc: RequestValidationError):
    code, fields = "validation_error", []
    for e in exc.errors():
        fields.append(".".join(str(p) for p in e["loc"] if p != "body"))
        msg = str(e.get("ctx", {}).get("error", ""))
        if e["type"] == "value_error" and msg in KNOWN_CODES:
            code = msg
    return JSONResponse(status_code=422, content={"detail": {"code": code, "message_key": f"errors.{code}",
                                                              "fields": fields}})


UPLOADS = Path(__file__).resolve().parents[2] / "uploads"


@asynccontextmanager
async def lifespan(_app):
    db = get_db()
    await ensure_indexes(db)
    s = get_settings()
    if s.mongo_uri.startswith("mongomock://"):  # in-memory dev DB starts empty: seed demo logins
        if not s.seed_password:
            logging.getLogger(__name__).warning("SEED_PASSWORD unset in mongomock mode; demo password is demo12345")
            s.seed_password = "demo12345"
        from app.seed import seed

        await seed(db)
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
    app.include_router(admin_kb.router, prefix="/api")
    app.include_router(company.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(storefronts.router, prefix="/api")
    app.include_router(public.router, prefix="/api")
    app.include_router(compliance.router, prefix="/api")
    app.add_exception_handler(RequestValidationError, validation_handler)
    UPLOADS.mkdir(exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=UPLOADS), name="uploads")
    return app


app = create_app()
