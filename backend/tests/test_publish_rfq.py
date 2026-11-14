import io

from tests.conftest import onboarding_payload  # noqa: F401


async def _published(producer, db):
    p = await producer("Ali")
    c = p["client"]
    await db.storefronts.insert_one({
        "company_id": p["company"]["id"], "country": "DE", "slug": "bozkurt-test", "status": "draft",
        "template": "classic", "owner_id": "x",
        "site_config": {"de": {"hero": {"headline": "Hallo"}}, "en": {"hero": {"headline": "Hi"}},
                        "review": {"secret": 1}, "missing": ["x"], "review_language": "de", "template": "classic"}})
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
    for bad in ("review", "missing", "owner_id", "price_floor", "9.5"):
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
    assert lead["is_hot"] is True and lead["is_demo"] is False and lead["score"] == 0
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
