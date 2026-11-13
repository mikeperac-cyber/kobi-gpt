import pytest
from conftest import onboarding_payload
from helpers import assert_no_floor


async def test_other_user_gets_404_on_product(producer):
    a, b = await producer("Aaa"), await producer("Bbb")
    pid = a["product"]["id"]
    body = onboarding_payload()["product"]
    for r in (await b["client"].get(f"/api/products/{pid}"),
              await b["client"].put(f"/api/products/{pid}", json=body),
              await b["client"].delete(f"/api/products/{pid}"),
              await b["client"].get("/api/products/not-an-objectid")):
        assert r.status_code == 404 and r.json()["detail"]["code"] == "not_found"
    assert (await a["client"].get(f"/api/products/{pid}")).status_code == 200  # untouched


async def test_floor_absent_from_non_owner_responses(producer, db):
    from app.core.security import create_token, hash_password
    import httpx
    from app.main import create_app

    a, b = await producer("Aaa"), await producer("Bbb")
    pid = a["product"]["id"]
    res = await db.users.insert_one({"email": "admin@x.com", "password_hash": hash_password("password123"),
                                     "name": "Admin", "is_admin": True})
    admin = httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()), base_url="http://test")
    admin.cookies.set("kobi_session", create_token(str(res.inserted_id)))
    listing = (await b["client"].get("/api/products")).json()
    assert pid not in [p["id"] for p in listing]
    for r in (await b["client"].get(f"/api/products/{pid}"), await b["client"].get("/api/company"),
              await admin.get(f"/api/products/{pid}"),
              await admin.get("/api/products")):
        assert_no_floor(r.json())
    assert (await admin.get(f"/api/products/{pid}")).status_code == 404
    assert (await admin.get("/api/company")).status_code == 404
    await admin.aclose()


def test_public_product_drops_floor_and_helper_detects_leaks():
    from app.core.serialize import owner_product, public_product

    doc = {"_id": "x", "name_tr": "a", "price_floor": 3.0}
    assert "price_floor" not in public_product(doc) and owner_product(doc)["price_floor"] == 3.0
    with pytest.raises(AssertionError):
        assert_no_floor({"a": [{"price_floor": 1}]})
