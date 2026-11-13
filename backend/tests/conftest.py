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


class FakeLLM:
    """Pops responses in order; an Exception instance is raised. A callable maps prompt -> response."""

    def __init__(self, responses=None):
        self.responses = responses if responses is not None else []
        self.prompts: list[str] = []

    async def complete(self, prompt, images, timeout, json_mode):
        self.prompts.append(prompt)
        if callable(self.responses):
            return self.responses(prompt)
        r = self.responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


@pytest.fixture
def fake_llm():
    from app.services.llm_service import set_provider

    fake = FakeLLM()
    set_provider(fake)
    yield fake
    set_provider(None)


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from app.core.ratelimit import reset_all

    reset_all()
    yield


@pytest.fixture
async def admin_client(db, client):
    from app.core.security import create_token, hash_password

    res = await db.users.insert_one(
        {"email": "admin@x.com", "password_hash": hash_password("password123"), "name": "Admin",
         "is_admin": True, "ui_language": "tr", "created_at": None, "kvkk_consent_at": None}
    )
    client.cookies.set("kobi_session", create_token(str(res.inserted_id)))
    return client
