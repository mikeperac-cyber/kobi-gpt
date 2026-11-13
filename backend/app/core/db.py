from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        s = get_settings()
        _db = AsyncIOMotorClient(s.mongo_uri)[s.mongo_db]
    return _db


def set_db(db) -> None:
    global _db
    _db = db


async def ensure_indexes(db) -> None:
    await db.users.create_index("email", unique=True)
    await db.companies.create_index("owner_id", unique=True)
