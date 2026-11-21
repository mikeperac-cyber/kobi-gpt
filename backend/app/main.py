import logging
import os
from urllib.parse import urlparse
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.db import ensure_indexes, get_db
from app.routers import account, admin, admin_kb, auth, company, compliance, dashboard, demo, health, jobs, leads, logistics, messages, products, public, quotes, storefronts, uploads

KNOWN_CODES = {"password_too_long", "invalid_city", "invalid_certification", "photo_required", "gdpr_required", "invalid_email", "product_too_long"}


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
PRIVATE_PREFIXES = ("quotes/", "reports/")  # generated PDFs: only the authenticated PDF endpoints return them


class PublicUploads(StaticFiles):
    """/uploads minus generated documents. shortcut: path filter, not signed URLs; upgrade with S3 + signed URLs."""

    async def get_response(self, path: str, scope):
        norm = os.path.normpath(path).replace("\\", "/").lower() + "/"  # case-insensitive disks (Windows)
        if norm.startswith(PRIVATE_PREFIXES):
            raise StarletteHTTPException(404)
        return await super().get_response(path, scope)


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


WEAK_SECRETS = {"", "dev-secret-change-me", "change-me"}


def check_jwt_secret(s) -> None:
    """Public (non-localhost) deployments must not run with a guessable JWT secret."""
    if urlparse(s.frontend_origin).hostname not in {"localhost", "127.0.0.1"} and (
            s.jwt_secret in WEAK_SECRETS or len(s.jwt_secret) < 32):
        raise RuntimeError("Refusing to start: set JWT_SECRET to a private random value of 32+ characters")


def create_app() -> FastAPI:
    s = get_settings()
    check_jwt_secret(s)
    app = FastAPI(title="KOBI-GPT", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[get_settings().frontend_origin],
        allow_credentials=True,
        allow_methods=["*"],
        expose_headers=["X-Total-Count"],
        allow_headers=["*"],
    )
    app.include_router(health.router, prefix="/api")
    app.include_router(auth.router, prefix="/api")
    app.include_router(account.router, prefix="/api")
    app.include_router(admin.router, prefix="/api")
    app.include_router(admin_kb.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")
    app.include_router(company.router, prefix="/api")
    app.include_router(products.router, prefix="/api")
    app.include_router(uploads.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(jobs.router, prefix="/api")
    app.include_router(storefronts.router, prefix="/api")
    app.include_router(public.router, prefix="/api")
    app.include_router(compliance.router, prefix="/api")
    app.include_router(leads.router, prefix="/api")
    app.include_router(leads.pipeline_router, prefix="/api")
    app.include_router(messages.router, prefix="/api")
    app.include_router(quotes.router, prefix="/api")
    app.include_router(logistics.router, prefix="/api")
    app.add_exception_handler(RequestValidationError, validation_handler)
    UPLOADS.mkdir(exist_ok=True)
    app.mount("/uploads", PublicUploads(directory=UPLOADS), name="uploads")
    return app


app = create_app()
