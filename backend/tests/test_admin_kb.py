import pytest
from bson import ObjectId
from conftest import onboarding_payload  # noqa: F401
from helpers import load_kb_json

from app.seed import seed


@pytest.fixture
async def seeded(db, monkeypatch):
    monkeypatch.setenv("SEED_PASSWORD", "demo12345")
    from app.core.config import get_settings
    get_settings.cache_clear()
    await seed(db)


def rule(**over):
    r = {k: v for k, v in load_kb_json("kb_rules")[6].items()}
    r.update(over)
    return r


@pytest.mark.parametrize("method,path", [
    ("GET", "/api/admin/kb/rules"), ("POST", "/api/admin/kb/rules"), ("PUT", "/api/admin/kb/rules/R7"),
    ("POST", "/api/admin/kb/rules/R7/verify"), ("GET", "/api/admin/kb/rules/export.csv"),
    ("POST", "/api/admin/kb/rules/import")])
async def test_non_admin_403(client, producer, seeded, method, path):
    p = await producer("Ali")
    assert (await p["client"].request(method, path, json={})).status_code == 403
    assert (await client.get("/api/admin/kb/rules")).status_code == 401


async def test_formula_guard_and_size_cap(admin_client, db, seeded):
    await admin_client.put("/api/admin/kb/hs_codes/0802.51", json={
        "id": "0802.51", "sector": "gida", "description_tr": "=HYPERLINK(\"x\")", "description_en": "+1", "note_tr": "-2", "note_en": "@a"})
    r = await admin_client.get("/api/admin/kb/hs_codes/export.csv")
    text = r.content.decode("utf-8-sig")
    assert "'=HYPERLINK" in text and "'+1" in text and "'-2" in text and "'@a" in text
    assert (await admin_client.post("/api/admin/kb/hs_codes/import", content=r.content)).status_code == 200
    d = await db.kb_hs_codes.find_one({"id": "0802.51"})
    assert d["description_tr"] == '=HYPERLINK("x")' and d["note_en"] == "@a"
    big = b"x" * (2 * 1024 * 1024 + 1)
    r = await admin_client.post("/api/admin/kb/hs_codes/import", content=big)
    assert r.status_code == 413 and r.json()["detail"]["code"] == "file_too_large"


async def test_last_verified_is_utc_iso(admin_client, seeded):
    r = await admin_client.post("/api/admin/kb/rules/R7/verify")
    assert r.json()["last_verified"].endswith("+00:00")


