from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.core.config import get_settings

_db: AsyncIOMotorDatabase | None = None


def get_db() -> AsyncIOMotorDatabase:
    global _db
    if _db is None:
        s = get_settings()
        if s.mongo_uri.startswith("mongomock://"):  # dev-only in-memory mode, data is lost on restart
            from mongomock_motor import AsyncMongoMockClient

            _db = AsyncMongoMockClient()[s.mongo_db]
        else:
            _db = AsyncIOMotorClient(s.mongo_uri)[s.mongo_db]
    return _db


def set_db(db) -> None:
    global _db
    _db = db


async def ensure_indexes(db) -> None:
    await db.users.create_index("email", unique=True)
    await db.companies.create_index("owner_id", unique=True)
    await db.storefronts.create_index("slug", unique=True)
    await db.storefronts.create_index([("company_id", 1), ("country", 1)], unique=True)
    await db.classifications.create_index("product_id", unique=True)
