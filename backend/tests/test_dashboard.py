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
    await db.messages.insert_one({"lead_id": str(l1), "status": "draft"})
    await db.messages.insert_one({"lead_id": str(l1), "status": "sent"})
    await db.quotes.insert_one({"lead_id": str(l1), "status": "draft"})
    await db.storefronts.insert_one({"company_id": cid, "country": "DE", "slug": "ali", "status": "published"})
    await db.readiness_reports.insert_one({"product_id": pid, "score": 40, "created_at": datetime(2026, 1, 1)})
    await db.readiness_reports.insert_one({"product_id": pid, "score": 65, "created_at": datetime(2026, 2, 1)})
    d = (await p["client"].get("/api/dashboard")).json()
    assert d["leads"] == {"count": 2, "pending_approvals": 2}
    assert d["storefront"] == {"status": "published", "slug": "ali"}
    assert d["compliance"]["score"] == 65
    assert d["roadmap"] == {"profile": True, "storefront": True, "compliance": True, "first_quote": False}
    await db.quotes.insert_one({"lead_id": str(l1), "status": "sent"})
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
