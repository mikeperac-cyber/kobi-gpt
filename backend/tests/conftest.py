import httpx
import pytest
from mongomock_motor import AsyncMongoMockClient

from app.core.db import ensure_indexes, set_db
from app.main import create_app


@pytest.fixture
async def db():
    database = AsyncMongoMockClient()["kobigpt_test"]
    set_db(database)
    await ensure_indexes(database)
    yield database
    set_db(None)


@pytest.fixture
async def client(db):
    app = create_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_settings(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret-0123")
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


def onboarding_payload(**over):
    p = {
        "company": {"name": "Bozkurt Gıda", "city": "Gaziantep", "sector": "gida", "description_tr": "Fıstık işleme",
                    "founded_year": 2005, "employee_count": 25, "certifications": ["ISO 22000", "IATF 16949"],
                    "contact": {"phone": "+90 342 000 00 00", "email": "info@bozkurt.com", "website": None},
                    "logo_url": None, "min_order_note": "Min. 1 palet"},
        "product": {"name_tr": "Antep fıstığı", "description_tr": "Kavrulmuş", "material_or_ingredients": "fıstık",
                    "unit": "kg", "moq": 500, "unit_weight_kg": 1, "price_floor": 9.5,
                    "photos": ["/uploads/products/a.webp"]},
        "market": {"country_code": "DE"},
    }
    p.update(over)
    return p


@pytest.fixture
async def producer(db):
    """Factory: producer(name) -> {"user", "company", "product", "client"}; each has its own cookie jar."""
    clients = []

    async def make(name: str):
        c = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test")
        clients.append(c)
        r = await c.post("/api/auth/register", json={"name": name, "email": f"{name.lower()}@firma.com",
                                                      "password": "password123", "kvkk_consent": True})
        assert r.status_code == 201, r.text
        user = r.json()
        await db.uploads.insert_one({"url": "/uploads/products/a.webp", "user_id": user["id"]})  # as /uploads/image would
        r = await c.post("/api/onboarding", json=onboarding_payload())
        assert r.status_code == 201, r.text
        return {"user": user, "company": r.json()["company"], "product": r.json()["product"], "client": c}

    yield make
    for c in clients:
        await c.aclose()
