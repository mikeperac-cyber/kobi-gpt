"""Who owns which uploaded file. Photos/logos are client-supplied URL strings, so ownership is checked here
(never inferred from the string) before a doc may reference a file, and before account deletion removes one."""
from datetime import datetime, timezone

from fastapi import HTTPException


async def record_upload(db, url: str, user_id: str) -> None:
    await db.uploads.update_one({"url": url, "user_id": user_id}, {"$setOnInsert": {"created_at": datetime.now(timezone.utc)}},
                                upsert=True)


async def owned_urls(db, urls, user_id: str) -> set[str]:
    wanted = {u for u in urls if u}
    return {r["url"] async for r in db.uploads.find({"user_id": user_id, "url": {"$in": list(wanted)}})} if wanted else set()


async def require_owned(db, urls, user_id: str) -> None:
    wanted = {u for u in urls if u}
    if wanted - await owned_urls(db, wanted, user_id):
        raise HTTPException(422, {"code": "bad_photo", "message_key": "errors.bad_photo", "fields": ["photos"]})
