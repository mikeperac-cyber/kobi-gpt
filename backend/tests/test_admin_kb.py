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


async def test_non_admin_403(client, producer, seeded):
    p = await producer("Ali")
    for kind in ("rules", "incentives", "hs_codes"):
        assert (await p["client"].get(f"/api/admin/kb/{kind}")).status_code == 403
    assert (await p["client"].post("/api/admin/kb/rules/R7/verify")).status_code == 403
    assert (await client.get("/api/admin/kb/rules")).status_code == 401


async def test_verify_sets_fields(admin_client, db, seeded):
    admin = await db.users.find_one({"is_admin": True, "email": "admin@x.com"})
    r = await admin_client.post("/api/admin/kb/rules/R7/verify")
    assert r.status_code == 200
    d = await db.kb_rules.find_one({"id": "R7"})
    assert d["verified"] is True and d["verified_by"] == str(admin["_id"]) and d["last_verified"] is not None
    assert r.json()["verified"] is True and "_id" not in r.json()
    assert (await admin_client.post("/api/admin/kb/rules/NOPE/verify")).status_code == 404


async def test_edit_resets_verified(admin_client, db, seeded):
    await admin_client.post("/api/admin/kb/rules/R7/verify")
    r = await admin_client.put("/api/admin/kb/rules/R7", json=rule(summary_tr="Yeni özet"))
    assert r.status_code == 200, r.text
    d = await db.kb_rules.find_one({"id": "R7"})
    assert d["summary_tr"] == "Yeni özet"
    assert d["verified"] is False and d["last_verified"] is None and d["verified_by"] is None


async def test_validation_and_create(admin_client, seeded):
    base = "/api/admin/kb/rules"
    assert (await admin_client.post(base, json=rule(id="R7"))).status_code == 409
    assert (await admin_client.post(base, json=rule(id="R7"))).json()["detail"]["code"] == "kb_id_exists"
    for bad in ({"id": "X9"}, {"source_url": "javascript:alert(1)"}, {"level": "x"}, {"title_en": " "},
                {"sectors": ["nope"]}, {"side": "XX"}):
        r = await admin_client.post(base, json={**rule(id="R99"), **bad})
        assert r.status_code == 422, bad
    assert (await admin_client.post(base, json=rule(id="R99"))).status_code == 201
    assert (await admin_client.get("/api/admin/kb/rules?q=R99")).json()[0]["verified"] is False
    assert (await admin_client.get("/api/admin/kb/bogus")).status_code == 404


async def test_csv_roundtrip(admin_client, db, seeded):
    for kind, coll in (("rules", "kb_rules"), ("incentives", "kb_incentives"), ("hs_codes", "kb_hs_codes")):
        r = await admin_client.get(f"/api/admin/kb/{kind}/export.csv")
        assert r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbf")
        await admin_client.post(f"/api/admin/kb/{kind}/{'R7' if kind == 'rules' else 'I1' if kind == 'incentives' else '0802.51'}/verify")
        before = {d["id"]: d async for d in db[coll].find({}, {"_id": 0})}
        r2 = await admin_client.post(f"/api/admin/kb/{kind}/import", content=r.content, headers={"content-type": "text/csv"})
        assert r2.status_code == 200, r2.text
        after = {d["id"]: d async for d in db[coll].find({}, {"_id": 0})}
        assert after == before  # unchanged content keeps verification


async def test_csv_import_edits_cp1254_semicolon_and_all_or_nothing(admin_client, db, seeded):
    r = await admin_client.get("/api/admin/kb/hs_codes/export.csv")
    text = r.content.decode("utf-8-sig").replace(",", ";")
    lines = text.splitlines()
    # naive re-delimit is safe only when no cell has commas; build explicit CSV instead
    csv = "id;sector;description_tr;description_en;note_tr;note_en\n0802.51;gida;Şahin fıstığı;Shahin;;\n"
    await admin_client.post("/api/admin/kb/hs_codes/0802.51/verify")
    r = await admin_client.post("/api/admin/kb/hs_codes/import", content=csv.encode("cp1254"))
    assert r.status_code == 200
    d = await db.kb_hs_codes.find_one({"id": "0802.51"})
    assert d["description_tr"] == "Şahin fıstığı" and d["verified"] is False and lines
    bad = csv + "9999.99;gida;;x;;\n" + "1234.56;gida;ok;ok;;\n"
    r = await admin_client.post("/api/admin/kb/hs_codes/import", content=bad.encode("utf-8"))
    assert r.status_code == 422 and r.json()["detail"]["rows"][0]["row"] == 3
    assert await db.kb_hs_codes.find_one({"id": "1234.56"}) is None


async def test_admin_cannot_read_other_products(admin_client, producer, seeded):
    p = await producer("Bozkurt")
    pid = p["product"]["id"]
    assert (await admin_client.get(f"/api/products/{pid}")).status_code == 404
    assert (await admin_client.get("/api/products")).status_code == 404  # admin has no company
    assert (await admin_client.get("/api/admin/kb/rules")).status_code == 200
    assert "price_floor" not in (await admin_client.get("/api/admin/kb/hs_codes")).text
