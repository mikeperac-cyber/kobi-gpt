import httpx

from app.core import db as dbmod
from app.core.config import get_settings
from app.main import create_app
from app.services import storage_service


async def test_mongomock_mode_serves_and_seeds(monkeypatch, tmp_path):
    monkeypatch.setenv("MONGO_URI", "mongomock://")
    monkeypatch.delenv("SEED_PASSWORD", raising=False)
    get_settings.cache_clear()
    dbmod.set_db(None)
    storage_service.set_root(tmp_path)
    app = create_app()
    try:
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as c:
                assert (await c.get("/api/health")).status_code == 200
                r = await c.post("/api/auth/login", json={"email": "bozkurt@demo.local", "password": "demo12345"})
                assert r.status_code == 200, r.text
    finally:
        dbmod.set_db(None)
        storage_service.set_root(None)
