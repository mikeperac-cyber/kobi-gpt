import pytest

from app.core.config import get_settings
from app.core.security import verify_password
from app.models.company import CompanyIn
from app.models.product import ProductIn
from app.seed import seed
from app.seed.images import make_placeholder
from app.services import storage_service


@pytest.fixture
def seeded_env(monkeypatch, tmp_path):
    monkeypatch.setenv("SEED_PASSWORD", "demo-pass-123")
    get_settings.cache_clear()
    storage_service.set_root(tmp_path)
    yield tmp_path
    storage_service.set_root(None)


async def test_seed_is_idempotent(db, seeded_env):
    first = await seed(db)
    files = sorted(p.name for p in seeded_env.rglob("*.webp"))
    second = await seed(db)
    assert first == second
    assert sorted(p.name for p in seeded_env.rglob("*.webp")) == files  # no new photos on re-run
    assert await db.users.count_documents({}) == 4
    assert await db.companies.count_documents({}) == 3
    assert await db.products.count_documents({}) == 6
    assert await db.leads.count_documents({}) == 18
    assert len(files) == 12


async def test_users_and_demo_companies(db, seeded_env):
    await seed(db)
    assert (await db.users.find_one({"is_admin": True}))["email"]
    u = await db.users.find_one({"email": "bozkurt@demo.local"})
    assert verify_password("demo-pass-123", u["password_hash"]) and not u["is_admin"]
    c = await db.companies.find_one({"owner_id": str(u["_id"])})
    assert c["is_demo_company"] is True and c["city"] == "Gaziantep"
    CompanyIn(**{k: c[k] for k in CompanyIn.model_fields})
    prods = await db.products.find({"company_id": str(c["_id"])}).to_list(10)
    assert {p["name_tr"] for p in prods} == {"Kabuklu Kavrulmuş Antep Fıstığı", "İç Antep Fıstığı"}
    for p in prods:
        ProductIn(**{k: p[k] for k in ProductIn.model_fields})
        assert p["hs_code_confirmed"] is None and len(p["photos"]) == 2
        assert all(x.startswith("/uploads/products/") for x in p["photos"])
    assert (await db.markets.find_one({"company_id": str(c["_id"])}))["country_code"] == "DE"


async def test_seed_requires_password(db, monkeypatch, tmp_path):
    monkeypatch.setenv("SEED_PASSWORD", "")
    get_settings.cache_clear()
    storage_service.set_root(tmp_path)
    try:
        with pytest.raises(RuntimeError):
            await seed(db)
    finally:
        storage_service.set_root(None)


async def test_kb_ids_exact(db, seeded_env):
    await seed(db)
    assert {r["id"] async for r in db.kb_rules.find()} == {f"R{i}" for i in range(1, 16)}
    assert {r["id"] async for r in db.kb_incentives.find()} == {f"I{i}" for i in range(1, 10)}
    assert {r["id"] async for r in db.kb_hs_codes.find()} == {
        "0802.51", "0802.52", "2008.19", "6302.60", "6207.91", "6208.91", "7318.15", "7318.16"}


async def test_kb_records_bilingual(db, seeded_env):
    await seed(db)
    pairs = {"kb_rules": ["title", "summary", "what_to_do", "documents"],
             "kb_incentives": ["name", "summary", "what_to_do"], "kb_hs_codes": ["description"]}
    for coll, fields in pairs.items():
        async for r in db[coll].find():
            assert r["verified"] is False and r["last_verified"] is None
            for f in fields:
                assert r[f"{f}_tr"] and r[f"{f}_en"], (r["id"], f)
            assert coll == "kb_hs_codes" or r["source_url"].startswith("https://")


async def test_kb_constraints(db, seeded_env):
    await seed(db)
    r = {x["id"]: x async for x in db.kb_rules.find()}
    assert r["R1"]["country"] is None and r["R1"]["side"] == "TR"
    assert all(r[f"R{i}"]["country"] == "DE" for i in range(2, 16))
    assert r["R3"]["hs_prefixes"] == ["0802", "2008"] and r["R9"]["channel"] == "b2c"
    assert [k for k, v in r.items() if v["structural_use"]] == ["R15"]
    assert r["R11"]["sectors"] == ["tekstil", "diger"] and r["R6"]["level"] == "önerilen"
    i = {x["id"]: x async for x in db.kb_incentives.find()}
    assert i["I5"]["sectors"] == ["tekstil"] and i["I8"]["stages"] == ["finansman", "ilk_ihracat"]
    assert {x["provider"] for x in i.values()} <= {"Ticaret Bakanlığı", "KOSGEB", "Türk Eximbank", "TİM"}


async def test_demo_leads_marked(db, seeded_env):
    await seed(db)
    leads = await db.leads.find().to_list(100)
    assert len(leads) == 18
    for lead in leads:
        assert lead["is_demo"] is True and lead["email"].endswith("@example.com")
        assert lead["source"] == "demo" and lead["country"] == "DE" and lead["status"] == "new" and lead["score"] >= 30
        assert lead["source_note"] == "DEMO – kurgusal firma" and lead["company_id"]
    assert len({lead["email"] for lead in leads}) == 18


async def test_logistics_rates(db, seeded_env):
    await seed(db)
    rates = {r["key"]: r async for r in db.logistics_rates.find()}
    assert set(rates) == {"packaging_pct", "ltl_bands", "ftl", "courier"}
    assert rates["ftl"]["truck_capacity_kg"] == 24000 and len(rates["ltl_bands"]["bands"]) == 3
    assert all(r["label_tr"].startswith("ÖRNEK") for r in rates.values())


async def test_no_storefronts_seeded(db, seeded_env):
    await seed(db)
    assert await db.storefronts.count_documents({}) == 0


def test_placeholder_image():
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(make_placeholder("Kabuklu Fıstık ŞĞİ", "#3E7B4F")))
    assert img.size == (1200, 900)


async def test_reseed_updates_kb_text_but_keeps_verification(db, seeded_env):
    await seed(db)
    when = "2026-01-01"
    await db.kb_rules.update_one({"id": "R7"}, {"$set": {"summary_tr": "ESKİ", "verified": True, "last_verified": when}})
    await seed(db)
    r = await db.kb_rules.find_one({"id": "R7"})
    assert r["summary_tr"] != "ESKİ" and r["verified"] is True and r["last_verified"] == when


async def test_seed_records_photo_owners_and_backfills(db, seeded_env):
    await seed(db)
    await db.uploads.delete_many({})  # simulate a database seeded before the registry existed
    await seed(db)
    for c in await db.companies.find({}).to_list(10):
        for p in await db.products.find({"company_id": str(c["_id"])}).to_list(10):
            for url in p["photos"]:
                assert await db.uploads.find_one({"url": url, "user_id": c["owner_id"]}), url


async def test_demo_products_have_translated_names(db, seeded_env):
    await seed(db)
    prods = await db.products.find({"seed_key": {"$exists": True}}).to_list(50)
    assert prods and all(p.get("name_de") and p.get("name_en") for p in prods)
