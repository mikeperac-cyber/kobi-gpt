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


# --- sweep: every company-scoped route with an id path parameter ------------------------------------------------
# (method, path) -> JSON body needed to get past validation. Producer B calls each on producer A's resources and must
# get 404 (the handler's ownership check runs before any side effect). Adding a route with an id param fails
# test_sweep_covers_every_id_route until it is listed here.
_QUOTE_REJECT = {"reason": "no"}
SWEEP = {
    ("GET", "/api/products/{pid}"): None,
    ("PUT", "/api/products/{pid}"): "product",
    ("DELETE", "/api/products/{pid}"): None,
    ("GET", "/api/leads/{lead_id}"): None,
    ("PATCH", "/api/leads/{lead_id}"): {"status": "contacted"},
    ("GET", "/api/leads/{lead_id}/messages"): None,
    ("POST", "/api/leads/{lead_id}/draft"): {},
    ("POST", "/api/leads/{lead_id}/reply"): {"text": "hello"},
    ("POST", "/api/leads/{lead_id}/sample-task"): "sample",
    ("PUT", "/api/messages/{message_id}"): {"subject": "s", "body": "b"},
    ("POST", "/api/messages/{message_id}/approve"): None,
    ("POST", "/api/messages/{message_id}/reject"): _QUOTE_REJECT,
    ("GET", "/api/quotes/{quote_id}"): None,
    ("POST", "/api/quotes/{quote_id}/approve"): None,
    ("POST", "/api/quotes/{quote_id}/reject"): _QUOTE_REJECT,
    ("GET", "/api/quotes/{quote_id}/pdf"): None,
    ("PATCH", "/api/compliance/reports/{report_id}/items/{rule_id}"): {"done": True},
    ("POST", "/api/compliance/reports/{report_id}/next-steps"): None,
    ("GET", "/api/compliance/reports/{report_id}/pdf"): None,
    ("GET", "/api/jobs/{job_id}"): None,
    ("POST", "/api/notifications/{notification_id}/read"): None,
    ("DELETE", "/api/verifications/{vid}"): None,
}
# Same guarantee for ids passed in the query string / body (no path parameter, so not enumerable from app.routes).
SWEEP_OTHER = [
    ("GET", "/api/compliance/reports/latest?product_id={pid}", None),
    ("GET", "/api/quotes/suggest?product_id={pid}", None),
    ("GET", "/api/compliance/gtip?product_id={pid}", None),
    ("POST", "/api/compliance/gtip", {"product_id": "{pid}"}),
    ("POST", "/api/quotes", "quote_in"),
]
NOT_COMPANY_SCOPED = ("/api/admin", "/api/demo", "/api/public", "/api/auth")


def test_sweep_covers_every_id_route():
    from app.main import create_app

    # openapi() flattens nested/included routers, which app.routes does not
    found = {(m.upper(), path) for path, ops in create_app().openapi()["paths"].items()
             if "{" in path and not path.startswith(NOT_COMPANY_SCOPED) for m in ops}
    assert found == set(SWEEP), {"unlisted": found - set(SWEEP), "stale": set(SWEEP) - found}


async def test_ownership_all_routes(producer, db, fake_llm, tmp_path):
    import asyncio
    from datetime import datetime, timezone

    from app.services import agent_steps, storage_service
    from helpers import load_kb_json

    storage_service.set_root(tmp_path)  # PDFs the positive control generates stay out of /uploads
    await db.logistics_rates.insert_many(load_kb_json("logistics_rates"))

    a, b = await producer("Aaa"), await producer("Bbb")
    cid, pid = a["company"]["id"], a["product"]["id"]
    now = datetime.now(timezone.utc)
    ids = {"pid": pid}
    ids["lead_id"] = str((await db.leads.insert_one({"company_id": cid, "company_name": "L", "status": "new",
                                                     "country": "DE", "created_at": now})).inserted_id)
    for key, coll, doc in (
            ("message_id", "messages", {"lead_id": ids["lead_id"], "status": "draft", "direction": "outbound"}),
            ("job_id", "jobs", {"kind": "x", "status": "done"}),
            ("notification_id", "notifications", {"read": False}),
            ("vid", "verifications", {"status": "pending", "kind": "certificate", "name": "ISO 22000"})):
        ids[key] = str((await db[coll].insert_one({"company_id": cid, "created_at": now, **doc})).inserted_id)
    ids["report_id"] = str((await db.readiness_reports.insert_one(
        {"company_id": cid, "product_id": pid, "checklist": [{"rule_id": "r1", "done": False, "side": "TR", "level": "zorunlu", "title_tr": "t", "title_en": "t",
                        "source_url": "https://example.org", "summary": "s", "what_to_do": "w", "applies": True}],
         "created_at": now})).inserted_id)
    ids["rule_id"] = "r1"
    await db.classifications.insert_one({"company_id": cid, "product_id": pid, "candidates": [], "confirmed_code": None})
    bodies = {"product": onboarding_payload()["product"], "sample": {"product_id": pid, "sample_weight_kg": 1},
              "quote_in": {"lead_id": ids["lead_id"], "product_id": pid, "quantity": 1, "unit_price": 99,
                           "currency": "EUR", "incoterm": "EXW", "payment_terms": "lc", "valid_until": "2999-01-01"}}

    q = await a["client"].post("/api/quotes", json=bodies["quote_in"])  # a real quote, so the owner's PDF/GET succeed
    assert q.status_code == 201, q.text
    ids["quote_id"] = q.json()["id"]

    def sub(x):
        return x.format(**ids) if isinstance(x, str) else {k: sub(v) for k, v in x.items()} if isinstance(x, dict) else x

    calls = [(m, p, body) for (m, p), body in SWEEP.items()] + SWEEP_OTHER
    calls = [(m, p, bodies.get(b, b) if isinstance(b, str) else b) for m, p, b in calls]
    # Positive control: the owner must succeed on every GET and on the query/body-id routes with these exact ids,
    # otherwise a wrong fixture id would make B's 404 pass vacuously. (A's reads never mutate; the two POSTs create.)
    for method, path, body in calls:
        if method == "GET" or (method, path) in {("POST", "/api/compliance/gtip"), ("POST", "/api/quotes")}:
            r = await a["client"].request(method, sub(path), json=sub(body))
            assert r.status_code == (201 if path == "/api/quotes" else 200), ("owner", method, path, r.status_code, r.text[:200])
    await asyncio.gather(*agent_steps._tasks)  # let the gtip job (fake LLM, fails fast) finish before teardown
    storage_service.set_root(None)
    for method, path, body in calls:
        body = sub(body)
        r = await b["client"].request(method, sub(path), json=body)
        assert r.status_code == 404, (method, path, r.status_code, r.text[:200])  # never 403, never a success
        assert_no_floor(r.json())
    assert await db.products.count_documents({"company_id": cid}) == 1  # A's data untouched
    assert await db.quotes.count_documents({"company_id": cid}) == 2  # fixture quote + the positive-control one
    assert (await db.leads.find_one({"company_id": cid}))["status"] == "new"
