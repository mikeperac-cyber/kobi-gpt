import pytest
import io

from app.models.storefront import SiteConfig
from app.services.storefront_service import fallback_site_config, publish_blockers
from tests.conftest import onboarding_payload  # noqa: F401
from tests.helpers import publishable_site_config


async def _published(producer, db):
    p = await producer("Ali")
    c = p["client"]
    await db.storefronts.insert_one({
        "company_id": p["company"]["id"], "country": "DE", "slug": "bozkurt-test", "status": "draft",
        "template": "classic", "owner_id": "x",
        "site_config": {**publishable_site_config(missing=["x"]),
                        "review": {**publishable_site_config()["review"], "about": {"story": "GEHEIM-TR"}}}})
    return p, c


def rfq(**over):
    b = {"company_name": "Müller GmbH", "contact_name": "Hans", "email": "hans@mueller.de", "country": "DE",
         "products": ["Pistazien"], "quantity": "2 Paletten", "message": "Bitte Angebot", "gdpr_consent": True,
         "website_hp": ""}
    b.update(over)
    return b


async def test_public_404_until_published(producer, db, client):
    p, c = await _published(producer, db)
    assert (await client.get("/api/public/storefronts/bozkurt-test")).status_code == 404
    assert (await c.post("/api/storefronts/mine/publish")).status_code == 200
    r = await client.get("/api/public/storefronts/bozkurt-test")
    assert r.status_code == 200 and r.json()["slug"] == "bozkurt-test"


async def test_unpublish_hides(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await c.post("/api/storefronts/mine/unpublish")
    assert r.json()["status"] == "draft" and r.json()["unpublished_at"]
    assert (await client.get("/api/public/storefronts/bozkurt-test")).status_code == 404


async def test_public_payload_has_no_private_fields(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    body = (await client.get("/api/public/storefronts/bozkurt-test")).json()
    assert set(body["site_config"]) == {"de", "en", "template"}
    assert set(body) == {"site_config", "company", "legal", "slug"}
    text = str(body)
    for bad in ("GEHEIM-TR", "'missing'", "'blockers'", "owner_id", "price_floor", "9.5"):
        assert bad not in text
    assert body["company"]["name"] == "Bozkurt Gıda"
    assert "min_order_note" not in body["company"]


async def test_impressum_checklist(producer, db):
    p, c = await _published(producer, db)
    items = {i["field"]: i["present"] for i in (await c.get("/api/storefronts/mine/impressum-checklist")).json()}
    assert items["name"] and items["email"] and items["phone"] and items["address"]
    assert not items["representative"] and not items["register"]


async def test_rfq_creates_lead_and_notification(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await client.post("/api/public/storefronts/bozkurt-test/rfq", json=rfq())
    assert r.status_code == 201
    lead = await db.leads.find_one({})
    assert lead["company_id"] == p["company"]["id"] and lead["source"] == "rfq" and lead["status"] == "new"
    assert lead["is_hot"] is True and lead["is_demo"] is False and lead["score"] >= 40
    assert lead["notes"] == "Bitte Angebot" and lead["products_of_interest"] == ["Pistazien"]
    n = await db.notifications.find_one({})
    assert n["type"] == "rfq" and n["params"] == {"company": "Müller GmbH"} and n["read"] is False


async def test_rfq_validation(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    u = "/api/public/storefronts/bozkurt-test/rfq"
    assert (await client.post(u, json=rfq(gdpr_consent=False))).status_code == 422
    assert (await client.post(u, json=rfq(email="nope"))).status_code == 422
    assert (await client.post(u, json=rfq(country="de"))).status_code == 422
    assert (await client.post(u, json=rfq(message="x" * 2001))).status_code == 422
    assert await db.leads.count_documents({}) == 0


async def test_rfq_requires_gdpr(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await client.post("/api/public/storefronts/bozkurt-test/rfq", json=rfq(gdpr_consent=False))
    assert r.status_code == 422


async def test_rfq_honeypot_drops(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await client.post("/api/public/storefronts/bozkurt-test/rfq", json=rfq(website_hp="http://spam"))
    assert r.status_code == 204
    assert await db.leads.count_documents({}) == 0 and await db.notifications.count_documents({}) == 0


async def test_rfq_rate_limited(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    u = "/api/public/storefronts/bozkurt-test/rfq"
    for _ in range(5):
        assert (await client.post(u, json=rfq())).status_code == 201
    assert (await client.post(u, json=rfq())).status_code == 429


async def test_rfq_on_unpublished_404(producer, db, client):
    p, c = await _published(producer, db)
    r = await client.post("/api/public/storefronts/bozkurt-test/rfq", json=rfq())
    assert r.status_code == 404


async def test_qr_png(producer, db):
    p, c = await _published(producer, db)
    r = await c.get("/api/storefronts/mine/qr.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("over,code", [({"gdpr_consent": False}, "gdpr_required"), ({"email": "nope"}, "invalid_email"),
                                       ({"products": ["x" * 121]}, "product_too_long")])
async def test_rfq_validation_codes_are_specific(producer, db, client, over, code):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await client.post("/api/public/storefronts/bozkurt-test/rfq", json=rfq(**over))
    assert r.status_code == 422 and r.json()["detail"]["code"] == code


def test_publish_blockers_lists_required_only():
    cfg = fallback_site_config({"name": "Bozkurt Gıda", "city": "Gaziantep", "sector": "gida"}, [], "b2b", "tr")
    b = publish_blockers(cfg)
    assert b[0] == "products"
    assert "about.founded_year" not in " ".join(b) and "export_info.lead_time" not in " ".join(b)
    assert publish_blockers(SiteConfig.model_validate(publishable_site_config())) == []


def test_publish_blockers_names_language_and_field():
    data = publishable_site_config()
    data["en"]["rfq"]["intro"] = "  "
    data["de"]["products"][0]["name"] = None
    data["de"]["hero"]["headline"] = None
    b = publish_blockers(SiteConfig.model_validate(data))
    assert b == ["de.hero.headline", "de.products.0.name", "en.rfq.intro"]


async def test_publish_blocked_returns_422_with_list(producer, db):
    p = await producer("Ali")
    data = publishable_site_config()
    data["de"]["products"] = []
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "country": "DE", "slug": "leer",
                                     "status": "draft", "template": "natural", "site_config": data})
    r = await p["client"].post("/api/storefronts/mine/publish")
    assert r.status_code == 422
    d = r.json()["detail"]
    assert d["code"] == "publish_blocked" and d["message_key"] == "errors.publish_blocked"
    assert d["blockers"][0] == "products"
    assert (await db.storefronts.find_one({"slug": "leer"}))["status"] == "draft"


async def test_put_returns_blockers(producer, db):
    p = await producer("Ali")
    data = publishable_site_config()
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "country": "DE", "slug": "leer",
                                     "status": "draft", "template": "natural", "site_config": data})
    data["en"]["products"][0]["name"] = ""
    r = await p["client"].put("/api/storefronts/mine", json={"site_config": data, "slug": "leer", "template": "natural"})
    assert r.status_code == 200 and r.json()["site_config"]["blockers"] == ["en.products.0.name"]


async def test_already_published_incomplete_stays_public(producer, db, client):
    p = await producer("Ali")
    data = publishable_site_config()
    data["de"]["products"] = []
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "country": "DE", "slug": "alt",
                                     "status": "published", "template": "natural", "site_config": data})
    assert (await client.get("/api/public/storefronts/alt")).status_code == 200
    assert (await p["client"].post("/api/storefronts/mine/unpublish")).status_code == 200


async def test_share_page_has_preview_tags(producer, db, client):
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    r = await client.get("/api/public/storefronts/bozkurt-test/share")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/html")
    html = r.text
    for want in ('property="og:title"', 'property="og:url" content="http://localhost:5173/s/bozkurt-test"',
                 'name="twitter:card" content="summary_large_image"', 'application/ld+json',
                 '"@type": "Organization"', 'og:locale" content="de_DE"', 'rel="canonical"'):
        assert want in html, want
    for bad in ("GEHEIM-TR", "price_floor", "9.5"):
        assert bad not in html


async def test_share_page_escapes_text(producer, db, client):
    p, c = await _published(producer, db)
    await db.storefronts.update_one({"slug": "bozkurt-test"},
                                    {"$set": {"site_config.de.seo.title": 'A"<script>alert(1)</script>'}})
    await db.companies.update_one({}, {"$set": {"name": "Evil</script><script>x()</script>"}})
    await c.post("/api/storefronts/mine/publish")
    html = (await client.get("/api/public/storefronts/bozkurt-test/share")).text
    assert "<script>alert" not in html and "<script>x()" not in html
    assert "&quot;" in html and "&lt;script&gt;" in html
    ld = html.split('application/ld+json">', 1)[1].split("</script>", 1)[0]
    assert "</" not in ld and "<" not in ld


async def test_share_page_404_when_draft(producer, db, client):
    await _published(producer, db)
    assert (await client.get("/api/public/storefronts/bozkurt-test/share")).status_code == 404


async def test_share_page_lang_en(producer, db, client):
    p, c = await _published(producer, db)
    await db.storefronts.update_one({"slug": "bozkurt-test"}, {"$set": {"site_config.en.seo.title": "English Title"}})
    await c.post("/api/storefronts/mine/publish")
    html = (await client.get("/api/public/storefronts/bozkurt-test/share?lang=en")).text
    assert "<title>English Title</title>" in html and 'og:locale" content="en_GB"' in html and '<html lang="en">' in html


async def test_qr_url_matches_origin(producer, db):
    p, c = await _published(producer, db)
    assert (await c.get("/api/storefronts/mine/qr-url")).json() == {"url": "http://localhost:5173/s/bozkurt-test"}


async def test_whatsapp_never_uses_seeded_demo_number(producer, db, client, monkeypatch):
    from app.core.config import get_settings
    p, c = await _published(producer, db)
    await c.post("/api/storefronts/mine/publish")
    url = "/api/public/storefronts/bozkurt-test"
    assert (await client.get(url)).json()["company"]["whatsapp"] == "+90 342 000 00 00"  # real company: own phone
    await db.companies.update_one({}, {"$set": {"is_demo_company": True}})
    assert (await client.get(url)).json()["company"]["whatsapp"] is None
    monkeypatch.setenv("DEMO_WHATSAPP_PHONE", "+90 555 000 00 00")
    get_settings.cache_clear()
    assert (await client.get(url)).json()["company"]["whatsapp"] == "+90 555 000 00 00"
