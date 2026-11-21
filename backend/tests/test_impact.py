from datetime import datetime, timedelta, timezone

from bson import ObjectId

from tests.helpers import assert_no_floor, publishable_site_config

T0 = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


async def _setup(db, p, start=T0):
    await db.users.update_one({"_id": ObjectId(p["user"]["id"])}, {"$set": {"created_at": start}})
    return p["company"]["id"], p["product"]["id"]


async def test_impact_null_until_events(producer, db):
    p = await producer("Ali")
    r = await p["client"].get("/api/dashboard/impact")
    assert r.status_code == 200
    j = r.json()
    assert j["storefront_published_at"] is None and j["first_report_at"] is None
    assert j["first_approved_outreach_at"] is None
    assert j["durations_s"] == {"to_storefront": None, "to_report": None, "to_outreach": None}
    assert j["measured_from"] == "signup" and j["signup_at"]


async def test_impact_durations_from_timestamps(producer, db):
    p = await producer("Ali")
    cid, pid = await _setup(db, p)
    await db.storefronts.insert_one({"company_id": cid, "status": "draft", "published_at": T0 + timedelta(seconds=252),
                                     "first_published_at": T0 + timedelta(seconds=100)})
    await db.readiness_reports.insert_one({"product_id": pid, "created_at": T0 + timedelta(hours=2, minutes=5)})
    await db.readiness_reports.insert_one({"product_id": pid, "created_at": T0 + timedelta(days=5)})
    for kind, d in (("cold", 4), ("rfq_answer", 3)):
        await db.messages.insert_one({"company_id": cid, "direction": "outbound", "status": "sent", "kind": kind,
                                      "approved_at": T0 + timedelta(days=d)})
    await db.messages.insert_one({"company_id": cid, "direction": "outbound", "status": "draft", "kind": "cold",
                                  "approved_at": T0 + timedelta(seconds=1)})
    j = (await p["client"].get("/api/dashboard/impact")).json()
    assert j["durations_s"] == {"to_storefront": 100, "to_report": 7500, "to_outreach": 3 * 86400}


async def test_impact_demo_company_measured_from_reset(producer, db):
    p = await producer("Ali")
    cid, pid = await _setup(db, p)
    reset = T0 + timedelta(days=200)
    await db.companies.update_one({"_id": ObjectId(cid)}, {"$set": {"is_demo_company": True, "demo_reset_at": reset}})
    await db.readiness_reports.insert_one({"product_id": pid, "created_at": reset + timedelta(seconds=30)})
    j = (await p["client"].get("/api/dashboard/impact")).json()
    assert j["measured_from"] == "demo_reset"
    assert j["durations_s"]["to_report"] == 30


async def test_first_published_at_kept_on_republish(producer, db):
    p = await producer("Ali")
    c = p["client"]
    cid = p["company"]["id"]
    await db.storefronts.insert_one({"company_id": cid, "country": "DE", "status": "draft", "slug": "x-y", "site_config": publishable_site_config()})
    assert (await c.post("/api/storefronts/mine/publish")).status_code == 200
    first = (await db.storefronts.find_one({"company_id": cid}))["first_published_at"]
    await c.post("/api/storefronts/mine/unpublish")
    await c.post("/api/storefronts/mine/publish")
    doc = await db.storefronts.find_one({"company_id": cid})
    assert doc["first_published_at"] == first
    assert (await c.get("/api/dashboard/impact")).json()["storefront_published_at"] is not None


async def test_admin_stats_counts_only(admin_client, producer, db):
    p = await producer("Ali")
    cid, pid = await _setup(db, p)
    await db.storefronts.insert_one({"company_id": cid, "status": "published"})
    await db.readiness_reports.insert_one({"product_id": pid, "created_at": T0})
    await db.messages.insert_one({"company_id": cid, "direction": "outbound", "status": "sent", "approved_at": T0})
    await db.leads.insert_one({"company_id": cid, "source": "rfq"})
    await db.leads.insert_one({"company_id": cid, "source": "manual"})
    await db.companies.insert_one({"name": "DemoCo", "owner_id": "z", "is_demo_company": True})
    r = await admin_client.get("/api/admin/stats")
    assert r.status_code == 200
    j = r.json()
    assert j == {"companies": 2, "storefronts_published": 1, "reports": 1, "approved_messages": 1, "rfqs": 1,
                 "excluding_demo": {"companies": 1, "storefronts_published": 1, "reports": 1,
                                    "approved_messages": 1, "rfqs": 1}}
    assert "Bozkurt" not in r.text and "DemoCo" not in r.text
    assert_no_floor(j)


async def test_admin_stats_excludes_demo_activity(admin_client, producer, db):
    p = await producer("Ali")
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"is_demo_company": True}})
    await db.leads.insert_one({"company_id": p["company"]["id"], "source": "rfq"})
    j = (await admin_client.get("/api/admin/stats")).json()
    assert j["rfqs"] == 1 and j["excluding_demo"]["rfqs"] == 0 and j["excluding_demo"]["companies"] == 0


async def test_admin_stats_forbidden_for_producer(producer):
    p = await producer("Ali")
    assert (await p["client"].get("/api/admin/stats")).status_code == 403
