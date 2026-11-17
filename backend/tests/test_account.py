import json
import re
from pathlib import Path

import pytest
from bson import ObjectId

from app.services import storage_service
from conftest import onboarding_payload


async def _seed(db, who, tmp_path):
    """Give a producer one of everything company-scoped, with real files on disk."""
    cid, pid = who["company"]["id"], who["product"]["id"]
    storage_service.set_root(tmp_path)
    st = storage_service.get_storage()
    photo = await st.save(b"x", "products")
    logo = await st.save(b"x", "logos")
    rpdf = await st.save_file(b"%PDF", f"reports/{cid}", ".pdf")
    qpdf = await st.save_file(b"%PDF", f"quotes/{cid}", ".pdf")
    await db.products.update_one({"_id": ObjectId(pid)}, {"$set": {"photos": [photo]}})
    await db.companies.update_one({"_id": ObjectId(cid)}, {"$set": {"logo_url": logo}})
    for coll, extra in (("storefronts", {"slug": "s-{}", "country": "DE"}), ("classifications", {"product_id": pid}), ("leads", {}), ("messages", {}),
                        ("quotes", {"pdf_url": qpdf}), ("tasks", {}), ("notifications", {}), ("jobs", {}),
                        ("agent_runs", {}), ("demo_cache", {}), ("lead_imports", {})):
        await db[coll].insert_one({"company_id": cid, **{k: v.format(cid) if k == "slug" else v for k, v in extra.items()}})
    await db.readiness_reports.insert_one({"company_id": cid, "product_id": pid, "pdf_url": rpdf})
    for u in (photo, logo, rpdf, qpdf):
        await db.uploads.insert_one({"url": u, "user_id": who["user"]["id"]})
    return [photo, logo, rpdf, qpdf]


def _file(tmp_path, url):
    return tmp_path / url.removeprefix("/uploads/")


@pytest.fixture(autouse=True)
def _root():
    yield
    storage_service.set_root(None)


async def test_export_excludes_password_hash(producer, db, tmp_path):
    a, b = await producer("Aaa"), await producer("Bbb")
    await _seed(db, a, tmp_path)
    await db.leads.insert_one({"company_id": b["company"]["id"], "company_name": "Other Co"})
    r = await a["client"].get("/api/account/export")
    assert r.status_code == 200 and "kobi-gpt-export.json" in r.headers["content-disposition"]
    data = json.loads(r.text)
    assert "password_hash" not in r.text and data["user"]["email"] == "aaa@firma.com"
    assert data["company"]["id"] == a["company"]["id"]
    assert data["products"][0]["price_floor"] == 9.5  # the owner's own data
    assert len(data["readiness_reports"]) == 1 and len(data["leads"]) == 1 and len(data["quotes"]) == 1
    assert "Other Co" not in r.text
    assert not {"jobs", "agent_runs", "demo_cache", "lead_imports"} & set(data)


async def test_export_requires_login(client):
    assert (await client.get("/api/account/export")).status_code == 401


async def test_delete_requires_confirmation(producer, db):
    a = await producer("Aaa")
    c = a["client"]
    r = await c.request("DELETE", "/api/account", json={"confirm": "yes", "password": "password123"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "confirm_mismatch"
    r = await c.request("DELETE", "/api/account", json={"confirm": "SİL", "password": "wrong-password"})
    assert r.status_code == 401 and r.json()["detail"]["code"] == "bad_password"
    assert await db.users.count_documents({}) == 1 and await db.products.count_documents({}) == 1


async def test_delete_removes_everything_and_files(producer, db, tmp_path):
    a, b = await producer("Aaa"), await producer("Bbb")
    mine = await _seed(db, a, tmp_path)
    theirs = await _seed(db, b, tmp_path)
    r = await a["client"].request("DELETE", "/api/account", json={"confirm": "DELETE", "password": "password123"})
    assert r.status_code == 204 and "kobi_session" in r.headers["set-cookie"]
    cid = a["company"]["id"]
    for coll in ("storefronts", "classifications", "leads", "messages", "quotes", "tasks", "notifications", "jobs",
                 "agent_runs", "demo_cache", "lead_imports", "products", "markets"):
        assert await db[coll].count_documents({"company_id": cid}) == 0, coll
    assert await db.readiness_reports.count_documents({"product_id": a["product"]["id"]}) == 0
    assert await db.companies.count_documents({"owner_id": a["user"]["id"]}) == 0
    assert await db.users.find_one({"_id": ObjectId(a["user"]["id"])}) is None
    assert not any(_file(tmp_path, u).exists() for u in mine)
    assert all(_file(tmp_path, u).exists() for u in theirs)  # other companies untouched
    assert await db.products.count_documents({"company_id": b["company"]["id"]}) == 1
    assert (await a["client"].get("/api/auth/me")).status_code == 401


async def test_delete_refuses_admin_and_demo(admin_client, producer, db):
    r = await admin_client.request("DELETE", "/api/account", json={"confirm": "DELETE", "password": "password123"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "cannot_delete_demo"
    a = await producer("Aaa")
    await db.companies.update_one({"_id": ObjectId(a["company"]["id"])}, {"$set": {"is_demo_company": True}})
    r = await a["client"].request("DELETE", "/api/account", json={"confirm": "SİL", "password": "password123"})
    assert r.status_code == 409 and await db.users.count_documents({}) == 2


async def test_cors_only_frontend_origin(client):
    def pre(origin):
        return client.options("/api/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"})

    from app.core.config import get_settings

    origin = get_settings().frontend_origin
    assert "access-control-allow-origin" not in (await pre("http://evil.test")).headers
    assert (await pre(origin)).headers["access-control-allow-origin"] == origin


def test_frontend_dist_has_no_secrets():
    dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    if not dist.exists():
        pytest.skip("frontend not built")
    for p in dist.rglob("*"):
        if p.suffix in {".js", ".html", ".css", ".map"}:
            text = p.read_text(encoding="utf-8", errors="ignore")
            for needle in ("API_KEY", "ANTHROPIC", "OPENAI", "GEMINI"):
                assert needle not in text, f"{needle} in {p.name}"
            assert not re.search(r"sk-[A-Za-z0-9_-]{20,}", text), f"key-like string in {p.name}"  # bare "sk-" hits "task-"


async def test_upload_endpoint_records_owner_and_photo_must_be_owned(producer, db, tmp_path):
    import io

    from PIL import Image

    storage_service.set_root(tmp_path)
    a, b = await producer("Aaa"), await producer("Bbb")
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buf, "PNG")
    r = await b["client"].post("/api/uploads/image", files={"file": ("x.png", buf.getvalue(), "image/png")})
    theirs = r.json()["url"]
    assert await db.uploads.find_one({"url": theirs, "user_id": b["user"]["id"]})
    body = {**onboarding_payload()["product"], "photos": [theirs]}
    for method, path in (("POST", "/api/products"), ("PUT", f"/api/products/{a['product']['id']}")):
        r = await a["client"].request(method, path, json=body)
        assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_photo", (method, r.text)
    r = await a["client"].put("/api/company", json={**onboarding_payload()["company"], "logo_url": theirs})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_photo"
    r = await b["client"].post("/api/products", json=body)  # the uploader may use it
    assert r.status_code == 201


async def test_onboarding_rejects_foreign_photo(client, db):
    await client.post("/api/auth/register", json={"name": "Ali", "email": "ali@firma.com", "password": "password123",
                                                  "kvkk_consent": True})
    await db.uploads.insert_one({"url": "/uploads/products/a.webp", "user_id": "someone-else"})
    r = await client.post("/api/onboarding", json=onboarding_payload())
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_photo"


async def test_delete_never_removes_foreign_file_even_if_doc_references_it(producer, db, tmp_path):
    a, b = await producer("Aaa"), await producer("Bbb")
    theirs = await _seed(db, b, tmp_path)
    await db.products.update_one({"_id": ObjectId(a["product"]["id"])}, {"$set": {"photos": [theirs[0]]}})  # legacy doc
    await db.companies.update_one({"_id": ObjectId(a["company"]["id"])}, {"$set": {"logo_url": theirs[1]}})
    r = await a["client"].request("DELETE", "/api/account", json={"confirm": "SİL", "password": "password123"})
    assert r.status_code == 204
    assert all(_file(tmp_path, u).exists() for u in theirs)
    assert await db.uploads.count_documents({"user_id": b["user"]["id"]}) >= 4  # B's records kept


@pytest.mark.parametrize("word", ["SİL", "SIL", "sil", "Sil", " DELETE ", "delete"])
async def test_confirm_word_variants(producer, word):
    a = await producer("Aaa")
    r = await a["client"].request("DELETE", "/api/account", json={"confirm": word, "password": "password123"})
    assert r.status_code == 204, word


async def test_delete_removes_superseded_and_abandoned_uploads(producer, db, tmp_path):
    from app.services.upload_registry import record_upload

    a, b = await producer("Aaa"), await producer("Bbb")
    await _seed(db, a, tmp_path)
    theirs = await _seed(db, b, tmp_path)
    st = storage_service.get_storage()
    extra = [await st.save_file(b"%PDF", f"reports/{a['company']['id']}", ".pdf"),  # an older report download
             await st.save(b"x", "products")]  # a replaced / abandoned photo
    for u in extra:
        await record_upload(db, u, a["user"]["id"])
    r = await a["client"].request("DELETE", "/api/account", json={"confirm": "DELETE", "password": "password123"})
    assert r.status_code == 204
    assert not any(_file(tmp_path, u).exists() for u in extra)
    assert all(_file(tmp_path, u).exists() for u in theirs)
    assert await db.uploads.count_documents({"user_id": a["user"]["id"]}) == 0
