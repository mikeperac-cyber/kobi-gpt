from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import RateLimiter
from app.core.security import (
    COOKIE_NAME, TOKEN_DAYS, create_token, current_user, hash_password, verify_password,
)
from app.models.auth import LanguageIn, LoginIn, RegisterIn

router = APIRouter(prefix="/auth")
_limiter = RateLimiter(10, 60)


def _set_cookie(resp: Response, user_id: str) -> None:
    resp.set_cookie(
        COOKIE_NAME, create_token(user_id), max_age=TOKEN_DAYS * 86400, httponly=True,
        samesite="lax", secure=get_settings().frontend_origin.startswith("https"),
    )


async def _me(user: dict) -> dict:
    has_company = await get_db().companies.find_one({"owner_id": str(user["_id"])}) is not None
    return {"id": str(user["_id"]), "name": user["name"], "email": user["email"],
            "is_admin": bool(user.get("is_admin")), "ui_language": user.get("ui_language", "tr"),
            "has_company": has_company}


def _limit(request: Request, email: str) -> None:
    _limiter.check(f"{request.client.host if request.client else '-'}|{email}")


@router.post("/register", status_code=201)
async def register(body: RegisterIn, request: Request, response: Response):
    _limit(request, body.email)
    users = get_db().users
    if await users.find_one({"email": body.email}):
        raise HTTPException(409, {"code": "email_taken", "message_key": "errors.email_taken"})
    now = datetime.now(timezone.utc)
    doc = {"email": body.email, "password_hash": hash_password(body.password), "name": body.name.strip(),
           "is_admin": False, "ui_language": "tr", "created_at": now, "kvkk_consent_at": now}
    doc["_id"] = (await users.insert_one(doc)).inserted_id
    _set_cookie(response, str(doc["_id"]))
    return await _me(doc)


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    _limit(request, body.email)
    user = await get_db().users.find_one({"email": body.email})
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, {"code": "invalid_credentials", "message_key": "errors.invalid_credentials"})
    _set_cookie(response, str(user["_id"]))
    return await _me(user)


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me(user: dict = Depends(current_user)):
    return await _me(user)


@router.patch("/me")
async def update_me(body: LanguageIn, user: dict = Depends(current_user)):
    await get_db().users.update_one({"_id": user["_id"]}, {"$set": {"ui_language": body.ui_language}})
    return await _me({**user, "ui_language": body.ui_language})
