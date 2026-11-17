from conftest import onboarding_payload

REG = {"name": "Ali", "email": "ali@firma.com", "password": "password123", "kvkk_consent": True}


async def _logged_in(client):
    uid = (await client.post("/api/auth/register", json=REG)).json()["id"]
    from app.core.db import get_db

    await get_db().uploads.insert_one({"url": "/uploads/products/a.webp", "user_id": uid})  # as /uploads/image would


async def test_onboarding_creates_company_product_market(client, db):
    await _logged_in(client)
    r = await client.post("/api/onboarding", json=onboarding_payload())
    assert r.status_code == 201
    body = r.json()
    assert body["company"]["city"] == "Gaziantep" and body["product"]["price_floor"] == 9.5
    assert await db.markets.count_documents({"country_code": "DE"}) == 1
    assert await db.products.count_documents({}) == 1
    assert (await client.get("/api/auth/me")).json()["has_company"] is True
    r = await client.post("/api/onboarding", json=onboarding_payload())
    assert r.status_code == 409 and r.json()["detail"]["code"] == "company_exists"


async def test_onboarding_requires_login_and_a_photo(client):
    assert (await client.post("/api/onboarding", json=onboarding_payload())).status_code == 401
    await _logged_in(client)
    p = onboarding_payload()
    p["product"]["photos"] = []
    assert (await client.post("/api/onboarding", json=p)).status_code == 422


async def test_only_de_market_allowed(client):
    await _logged_in(client)
    r = await client.post("/api/onboarding", json=onboarding_payload(market={"country_code": "FR"}))
    assert r.status_code == 422


async def test_city_must_be_province(client):
    await _logged_in(client)
    p = onboarding_payload()
    p["company"]["city"] = "Atlantis"
    r = await client.post("/api/onboarding", json=p)
    assert r.status_code == 422
    assert r.json()["detail"] == {"code": "invalid_city", "message_key": "errors.invalid_city",
                                  "fields": ["company.city"]}


async def test_validation_error_convention(client):
    r = await client.post("/api/auth/register", json={**REG, "password": "short"})
    assert r.json()["detail"] == {"code": "validation_error", "message_key": "errors.validation_error",
                                  "fields": ["password"]}


def test_provinces_and_certs():
    from app.models.company import CERTS
    from app.models.provinces import TR_PROVINCES

    assert len(TR_PROVINCES) == 81 == len(set(TR_PROVINCES))
    assert {"İstanbul", "İzmir", "Şanlıurfa", "Kahramanmaraş", "Düzce", "Adana"} <= set(TR_PROVINCES)
    assert "IATF 16949" in CERTS


async def test_owner_sees_floor(producer):
    a = await producer("Aaa")
    r = await a["client"].get("/api/products")
    assert r.json()[0]["price_floor"] == 9.5
    pid = a["product"]["id"]
    assert (await a["client"].get(f"/api/products/{pid}")).json()["price_floor"] == 9.5
    body = {**onboarding_payload()["product"], "price_floor": 12, "photos": []}
    r = await a["client"].put(f"/api/products/{pid}", json=body)
    assert r.status_code == 200 and r.json()["price_floor"] == 12
    r = await a["client"].post("/api/products", json=body)
    assert r.status_code == 201 and len((await a["client"].get("/api/products")).json()) == 2
    assert (await a["client"].delete(f"/api/products/{pid}")).status_code == 200
    assert (await a["client"].get(f"/api/products/{pid}")).status_code == 404


async def test_company_get_put(producer):
    a = await producer("Aaa")
    assert (await a["client"].get("/api/company")).json()["name"] == "Bozkurt Gıda"
    body = {**onboarding_payload()["company"], "name": "Yeni Ad", "city": "İzmir"}
    r = await a["client"].put("/api/company", json=body)
    assert r.status_code == 200 and r.json()["name"] == "Yeni Ad"
    assert (await a["client"].get("/api/company")).json()["city"] == "İzmir"


async def test_no_company_404(client):
    await _logged_in(client)
    r = await client.get("/api/company")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "no_company"
    assert (await client.get("/api/products")).status_code == 404


async def test_invalid_product_values(producer):
    a = await producer("Aaa")
    base = onboarding_payload()["product"]
    for bad in ({"moq": 0}, {"price_floor": -1}, {"unit": "ton"}, {"unit_weight_kg": 0}, {"photos": ["x"] * 7}):
        r = await a["client"].post("/api/products", json={**base, **bad})
        assert r.status_code == 422, bad
    r = await a["client"].post("/api/products", json={**base, "unit_weight_kg": None})
    assert r.status_code == 201
