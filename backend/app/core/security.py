from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from bson import ObjectId
from bson.errors import InvalidId
from fastapi import Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.db import get_db

COOKIE_NAME = "kobi_session"
TOKEN_DAYS = 7


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p: str, h: str) -> bool:
    if len(p.encode()) > 72:  # bcrypt limit
        return False
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def create_token(user_id: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS)
    return jwt.encode({"sub": user_id, "exp": exp}, get_settings().jwt_secret, algorithm="HS256")


def _unauth():
    return HTTPException(401, {"code": "unauthenticated", "message_key": "errors.unauthenticated"})


async def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise _unauth()
    try:
        claims = jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"],
                            options={"require": ["exp", "sub"]})
        uid = ObjectId(claims["sub"])
    except (jwt.PyJWTError, InvalidId, KeyError, TypeError):
        raise _unauth()
    user = await get_db().users.find_one({"_id": uid})
    if not user:
        raise _unauth()
    return user


async def require_admin(user: dict = Depends(current_user)) -> dict:
    if not user.get("is_admin"):
        raise HTTPException(403, {"code": "forbidden", "message_key": "errors.forbidden"})
    return user


async def current_company(user: dict = Depends(current_user)) -> dict:
    company = await get_db().companies.find_one({"owner_id": str(user["_id"])})
    if not company:
        raise HTTPException(404, {"code": "no_company", "message_key": "errors.no_company"})
    return company


async def owned(collection: str, id: str, company_id: str) -> dict:
    """Company-scoped fetch. Missing, foreign or malformed ids all give 404 (no existence leak)."""
    try:
        oid = ObjectId(id)
    except (InvalidId, TypeError):
        oid = None
    doc = await get_db()[collection].find_one({"_id": oid, "company_id": company_id}) if oid else None
    if not doc:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return doc
