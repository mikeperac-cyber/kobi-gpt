import json

import pytest
from bson import ObjectId

from app.core.config import get_settings
from app.seed import seed
from app.services import storage_service
from app.services.agent_steps import cache_key, create_job, run_ai_step
from app.services.demo_service import reset_demo_company
from app.services.llm_service import LLMProviderError
from tests.helpers import assert_no_floor
from tests.test_gtip import _run as run_gtip, cand, kb  # noqa: F401
from tests.test_storefront_generation import INTAKE, _generate, _llm


@pytest.fixture
def seeded(monkeypatch, tmp_path):
    monkeypatch.setenv("SEED_PASSWORD", "demo-pass-123")
    get_settings.cache_clear()
    storage_service.set_root(tmp_path)
    yield
    storage_service.set_root(None)


def _failing(_prompt):
    raise LLMProviderError("no key")


async def _bozkurt(db):
    return await db.companies.find_one({"name": "Bozkurt Antep Fıstığı"})


async def test_reset_clean_state_under_3s(db, seeded):
    await seed(db)
    c = await _bozkurt(db)
    cid = str(c["_id"])
    prods = await db.products.find({"company_id": cid}).to_list(10)
    pid = prods[0]["_id"]
    lead = await db.leads.find_one({"company_id": cid, "is_demo": True})
    for coll in ("storefronts", "classifications", "readiness_reports", "messages", "quotes", "tasks",
                 "notifications", "jobs", "lead_imports"):
        await db[coll].insert_one({"company_id": cid, "slug": "x", "country": "DE", "product_id": "p"})
    await db.leads.insert_one({"company_id": cid, "source": "rfq", "email": "x@y.de", "is_demo": False})
    await db.demo_cache.insert_one({"company_id": cid, "key": "k", "output": 1})
    await db.products.update_one({"_id": pid}, {"$set": {"hs_code_confirmed": "2008.19", "price_floor": 1.0,
                                                         "photos": ["/uploads/x.webp"], "name_tr": prods[0]["name_tr"]}})
    await db.companies.update_one({"_id": c["_id"]}, {"$set": {"description_tr": "değişti"}})
    await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "sent", "score": 1}})
    out = await reset_demo_company(db, "gaziantep")
    assert out["elapsed_ms"] < 3000  # mongomock; a real Mongo adds a few round trips, still well below
    for coll in ("storefronts", "classifications", "readiness_reports", "messages", "quotes", "tasks",
                 "notifications", "jobs", "lead_imports"):
        assert await db[coll].count_documents({"company_id": cid}) == 0
    assert await db.demo_cache.count_documents({"company_id": cid}) == 1
    assert await db.leads.count_documents({"company_id": cid}) == 6
    after = await db.leads.find_one({"_id": lead["_id"]})
    assert after["status"] == "new" and after["score"] != 1
    p = await db.products.find_one({"_id": pid})
    assert p["hs_code_confirmed"] is None and p["price_floor"] != 1.0 and p["photos"] != ["/uploads/x.webp"]
    assert (await _bozkurt(db))["description_tr"] != "değişti"
    assert await db.users.find_one({"email": "bozkurt@demo.local"})


async def test_reset_twice_idempotent(db, seeded):
    await seed(db)
    await reset_demo_company(db, "denizli")

    async def snap():
        return [await db[c].find({}, {"created_at": 0, "demo_reset_at": 0}).sort("_id").to_list(100)
                for c in ("companies", "products", "leads")]

    first = await snap()
    await reset_demo_company(db, "denizli")
    assert await snap() == first


async def test_reset_unseeded_returns_none(db):
    assert await reset_demo_company(db, "bursa") is None


async def test_demo_reset_admin_only(db, client, seeded):
    await seed(db)
    assert (await client.post("/api/demo/reset/gaziantep")).status_code == 401
    from app.core.security import create_token
    u = await db.users.find_one({"email": "bozkurt@demo.local"})
    client.cookies.set("kobi_session", create_token(str(u["_id"])))
    assert (await client.post("/api/demo/reset/gaziantep")).status_code == 403
    a = await db.users.find_one({"is_admin": True})
    client.cookies.set("kobi_session", create_token(str(a["_id"])))
    r = await client.post("/api/demo/reset/gaziantep")
    assert r.status_code == 200 and "elapsed_ms" in r.json()
    assert (await client.post("/api/demo/reset/izmir")).status_code == 404
    names = {c["key"] for c in (await client.get("/api/demo/companies")).json()}
    assert names == {"gaziantep", "denizli", "bursa"}


async def _make_demo(db, p):
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"is_demo_company": True}})


async def test_cache_used_when_llm_fails(producer, fake_llm, db, kb):
    p = await producer("Ali")
    await _make_demo(db, p)
    fake_llm.responses = _llm(p)
    assert (await _generate(p))["status"] == "done"
    good = (await p["client"].get("/api/storefronts/mine")).json()["site_config"]
    fake_llm.responses = [json.dumps({"candidates": [cand("200819")]})]
    live = (await run_gtip(p, "roasted"))["result"]["candidates"]
    assert await db.demo_cache.count_documents({}) == 4  # analysis, adaptation, content, gtip

    fake_llm.responses = _failing  # the key is gone
    job = await _generate(p)
    assert [s["source"] for s in job["steps"]] == ["cache"] * 3 + ["template"]
    assert [s["status"] for s in job["steps"]] == ["fallback"] * 3 + ["done"]
    assert (await p["client"].get("/api/storefronts/mine")).json()["site_config"] == good
    gj = await run_gtip(p, "roasted")
    assert gj["result"]["candidates"] == live and gj["steps"][0]["source"] == "cache"
    for d in await db.demo_cache.find({}).to_list(50):
        assert_no_floor(d["output"])
        assert "9.5" not in json.dumps(d["output"])


async def test_cache_key_includes_language(db):
    co = {"_id": ObjectId(), "is_demo_company": True}

    async def ok(t): return "tr-out"

    async def bad(t): raise LLMProviderError("x")

    await run_ai_step(None, "s", co, ok, lambda: "tpl", cache_key("s", "tr", "d"))
    assert await run_ai_step(None, "s", co, bad, lambda: "tpl", cache_key("s", "tr", "d")) == ("tr-out", True)
    assert await run_ai_step(None, "s", co, bad, lambda: "tpl", cache_key("s", "en", "d")) == ("tpl", True)


async def test_non_demo_company_never_touches_cache(db):
    co = {"_id": ObjectId()}

    async def ok(t): return "out"

    async def bad(t): raise LLMProviderError("x")

    await run_ai_step(None, "s", co, ok, lambda: "tpl", "k")
    assert await db.demo_cache.count_documents({}) == 0
    await db.demo_cache.insert_one({"company_id": str(co["_id"]), "key": "k", "output": "stale"})
    assert await run_ai_step(None, "s", co, bad, lambda: "tpl", "k") == ("tpl", True)


async def test_unusable_cache_entry_falls_back_to_template(db):
    co = {"_id": ObjectId(), "is_demo_company": True}
    await db.demo_cache.insert_one({"company_id": str(co["_id"]), "key": "k", "output": {"bad": 1}})

    async def bad(t): raise LLMProviderError("x")

    def restore(v): raise ValueError("schema drift")

    assert await run_ai_step(None, "s", co, bad, lambda: "tpl", "k", restore) == ("tpl", True)


async def test_reset_restores_renamed_and_deleted_products(db, seeded):
    await seed(db)
    cid = str((await _bozkurt(db))["_id"])
    a, b = await db.products.find({"company_id": cid}).sort("_id", 1).to_list(10)
    await db.products.update_one({"_id": a["_id"]}, {"$set": {"name_tr": "Başka ad"}})
    await db.products.delete_one({"_id": b["_id"]})
    await db.products.insert_one({"company_id": cid, "name_tr": "Ekstra", "photos": []})
    await reset_demo_company(db, "gaziantep")
    got = await db.products.find({"company_id": cid}).sort("_id", 1).to_list(10)
    assert [p["name_tr"] for p in got] == [a["name_tr"], b["name_tr"]]
    assert got[0]["_id"] == a["_id"] and got[1]["photos"] and len({p["seed_key"] for p in got}) == 2


async def test_legacy_products_without_seed_key_are_backfilled(db, seeded):
    await seed(db)
    cid = str((await _bozkurt(db))["_id"])
    a = await db.products.find_one({"company_id": cid, "seed_key": "bozkurt:0"})
    await db.products.update_many({"company_id": cid}, {"$unset": {"seed_key": "", "seed_photos": ""}})
    await db.products.update_one({"_id": a["_id"]}, {"$set": {"name_tr": "Eski ad"}})
    await reset_demo_company(db, "gaziantep")
    p = await db.products.find_one({"_id": a["_id"]})
    assert p["name_tr"] == a["name_tr"] and p["seed_key"] == "bozkurt:0" and p["seed_photos"]
    assert await db.products.count_documents({"company_id": cid}) == 2


async def test_cache_hit_rechecks_floor_and_known_ids(db):
    from app.services.regai_service import next_steps
    co = {"_id": ObjectId(), "is_demo_company": True}
    await db.demo_cache.insert_one({"company_id": str(co["_id"]), "key": "next_steps:tr:s", "output": [
        {"rule_id": "GONE", "text": "x"}]})
    checklist = [{"rule_id": "R1", "applies": True, "done": False, "level": "zorunlu", "title_tr": "t"}]
    rules = {"R1": {"summary_tr": "s", "title_tr": "t", "what_to_do_tr": "w"}}
    out = await next_steps(checklist, rules, co, "tr", None, "s")  # LLM not configured -> cache hit
    assert out == []
