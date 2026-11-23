from datetime import datetime, timezone

NOW = datetime.now(timezone.utc)


async def _lead(db, cid, n=1):
    return [(await db.leads.insert_one({"company_id": cid, "status": "new", "email": f"l{i}@x.de"})).inserted_id
            for i in range(n)]


async def test_dashboard_fresh_company(producer):
    p = await producer("Ali")
    d = (await p["client"].get("/api/dashboard")).json()
    assert d["company"] == {"name": "Bozkurt Gıda", "country_code": "DE"}
    assert d["storefront"] == {"status": "none", "slug": None}
    assert d["compliance"] == {"score": None}
    assert d["leads"] == {"count": 0, "pending_approvals": 0}
    assert d["roadmap"] == {"profile": True, "storefront": False, "compliance": False, "first_quote": False}
    assert d["notifications"] == []


async def test_dashboard_counts_real(producer, db):
    p = await producer("Ali")
    cid, pid = p["company"]["id"], p["product"]["id"]
    l1, _ = await _lead(db, cid, 2)
    await db.messages.insert_one({"lead_id": str(l1), "status": "draft", "company_id": cid})
    await db.messages.insert_one({"lead_id": str(l1), "status": "sent", "company_id": cid})
    await db.quotes.insert_one({"lead_id": str(l1), "status": "draft", "company_id": cid})
    await db.storefronts.insert_one({"company_id": cid, "country": "DE", "slug": "ali", "status": "published"})
    await db.readiness_reports.insert_one({"product_id": pid, "score": 40, "created_at": datetime(2026, 1, 1)})
    await db.readiness_reports.insert_one({"product_id": pid, "score": 65, "created_at": datetime(2026, 2, 1)})
    d = (await p["client"].get("/api/dashboard")).json()
    assert d["leads"] == {"count": 2, "pending_approvals": 2}
    assert d["storefront"] == {"status": "published", "slug": "ali"}
    assert d["compliance"]["score"] == 65
    assert d["roadmap"] == {"profile": True, "storefront": True, "compliance": True, "first_quote": False}
    await db.quotes.insert_one({"lead_id": str(l1), "status": "sent", "company_id": cid})
    assert (await p["client"].get("/api/dashboard")).json()["roadmap"]["first_quote"] is True


async def test_dashboard_scoped_to_owner(producer, db):
    a, b = await producer("Ali"), await producer("Veli")
    (lid,) = await _lead(db, a["company"]["id"])
    await db.messages.insert_one({"lead_id": str(lid), "status": "draft"})
    await db.readiness_reports.insert_one({"product_id": a["product"]["id"], "score": 90, "created_at": NOW})
    await db.storefronts.insert_one({"company_id": a["company"]["id"], "country": "DE", "slug": "a", "status": "draft"})
    await db.notifications.insert_one({"company_id": a["company"]["id"], "type": "rfq", "params": {}, "read": False,
                                      "created_at": NOW})
    d = (await b["client"].get("/api/dashboard")).json()
    assert d["leads"]["count"] == 0 and d["leads"]["pending_approvals"] == 0
    assert d["compliance"]["score"] is None and d["storefront"]["status"] == "none" and d["notifications"] == []


async def test_notifications_order_and_read(producer, db):
    a, b = await producer("Ali"), await producer("Veli")
    cid = a["company"]["id"]
    old = (await db.notifications.insert_one({"company_id": cid, "type": "rfq", "params": {"company": "X"},
                                              "read": False, "created_at": datetime(2026, 1, 1)})).inserted_id
    new = (await db.notifications.insert_one({"company_id": cid, "type": "rfq", "params": {"company": "Y"},
                                              "read": False, "created_at": datetime(2026, 2, 1)})).inserted_id
    n = (await a["client"].get("/api/dashboard")).json()["notifications"]
    assert [x["id"] for x in n] == [str(new), str(old)]
    assert n[0]["message_key"] == "dashboard.notif.rfq" and n[0]["params"] == {"company": "Y"}
    assert (await b["client"].post(f"/api/notifications/{new}/read")).status_code == 404
    assert (await a["client"].post(f"/api/notifications/{new}/read")).status_code == 200
    assert (await db.notifications.find_one({"_id": new}))["read"] is True


async def test_pending_ignores_other_company(producer, db):
    a, b = await producer("Ali"), await producer("Veli")
    lid = str((await _lead(db, b["company"]["id"], 1))[0])
    for coll in ("messages", "quotes"):
        await db[coll].insert_one({"lead_id": lid, "company_id": b["company"]["id"], "status": "draft"})
    await db.quotes.insert_one({"lead_id": lid, "company_id": b["company"]["id"], "status": "sent"})
    d = (await a["client"].get("/api/dashboard")).json()
    assert d["leads"] == {"count": 0, "pending_approvals": 0} and d["roadmap"]["first_quote"] is False
    assert (await b["client"].get("/api/dashboard")).json()["leads"]["pending_approvals"] == 2


async def _publish(db, p, slug):
    from tests.helpers import publishable_site_config
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "country": "DE", "slug": slug,
                                     "status": "published", "template": "natural",
                                     "site_config": publishable_site_config()})


def _rfq_body(company="Müller GmbH"):
    return {"company_name": company, "contact_name": "Hans", "email": "hans@mueller.de", "country": "DE",
            "products": ["Pistazien"], "quantity": "2 Paletten", "message": "Bitte Angebot",
            "gdpr_consent": True, "website_hp": ""}


async def test_since_baseline_then_new_rfq(producer, db, client):
    a = await producer("Ali")
    await _publish(db, a, "ali-shop")
    first = (await a["client"].get("/api/notifications/since")).json()
    assert first["items"] == [] and first["now"]
    assert (await client.post("/api/public/storefronts/ali-shop/rfq", json=_rfq_body())).status_code == 201
    second = (await a["client"].get("/api/notifications/since", params={"after": first["now"]})).json()
    assert len(second["items"]) == 1
    item = second["items"][0]
    lead = await db.leads.find_one({"source": "rfq", "company_id": a["company"]["id"]})
    assert item["type"] == "rfq" and item["params"]["company"] == "Müller GmbH"
    assert item["lead_id"] == str(lead["_id"])
    third = (await a["client"].get("/api/notifications/since", params={"after": second["now"]})).json()
    assert [i["id"] for i in third["items"]] in ([], [item["id"]])  # overlap window may repeat; client dedupes


async def test_since_scoped_to_company(producer, db, client):
    a, b = await producer("Ali"), await producer("Veli")
    await _publish(db, b, "veli-shop")
    first = (await a["client"].get("/api/notifications/since")).json()
    await client.post("/api/public/storefronts/veli-shop/rfq", json=_rfq_body())
    r = (await a["client"].get("/api/notifications/since", params={"after": first["now"]})).json()
    assert r["items"] == []


async def test_since_rejects_bad_after(producer):
    a = await producer("Ali")
    assert (await a["client"].get("/api/notifications/since", params={"after": "yesterday"})).status_code == 422


async def test_since_overlap_catches_late_insert(producer, db):
    from datetime import timedelta
    a = await producer("Ali")
    first = (await a["client"].get("/api/notifications/since")).json()
    after = datetime.fromisoformat(first["now"])
    # created just before the poll's "now" but inserted after it ran (slow write)
    await db.notifications.insert_one({"company_id": a["company"]["id"], "type": "rfq", "params": {"company": "X"},
                                       "read": False, "created_at": after - timedelta(milliseconds=3)})
    r = (await a["client"].get("/api/notifications/since", params={"after": first["now"]})).json()
    assert [i["params"]["company"] for i in r["items"]] == ["X"]
