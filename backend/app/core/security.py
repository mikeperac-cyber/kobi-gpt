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
