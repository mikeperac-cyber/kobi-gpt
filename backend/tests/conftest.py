import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.db import set_db
from app.main import create_app


@pytest.fixture
async def db():
    database = AsyncMongoMockClient()["kobigpt_test"]
    set_db(database)
    yield database
    set_db(None)


@pytest.fixture
async def client(db):
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_settings():
    from app.core.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
