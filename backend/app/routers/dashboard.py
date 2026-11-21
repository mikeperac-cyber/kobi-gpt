from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import current_company, current_user, owned
from app.core.serialize import to_json

router = APIRouter()


@router.get("/dashboard")
async def dashboard(company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    pids = [str(p["_id"]) async for p in db.products.find({"company_id": cid}, {"_id": 1})]
    market = await db.markets.find_one({"company_id": cid})
    sfs = await db.storefronts.find({"company_id": cid}).to_list(50)
    sf = next((s for s in sfs if s.get("status") == "published"), sfs[0] if sfs else None)
    report = (await db.readiness_reports.find_one({"product_id": {"$in": pids}}, sort=[("created_at", -1)])
              if pids else None)  # newest report across all the company's products
    own = {"company_id": cid}
    lead_count = await db.leads.count_documents(own)
    pending = (await db.messages.count_documents({**own, "status": "draft"})
               + await db.quotes.count_documents({**own, "status": "draft"}))
    sent_quote = await db.quotes.count_documents({**own, "status": "sent"})
    notes = await db.notifications.find(own).sort("created_at", -1).limit(20).to_list(20)
    return {
        "company": {"name": company["name"], "country_code": (market or {}).get("country_code", "DE")},
        "storefront": {"status": sf["status"] if sf else "none", "slug": sf.get("slug") if sf else None},
        "compliance": {"score": report.get("score") if report else None},
        "leads": {"count": lead_count, "pending_approvals": pending},
        "roadmap": {"profile": bool(pids), "storefront": bool(sf and sf["status"] == "published"),
                    "compliance": report is not None, "first_quote": sent_quote > 0},
        "notifications": [{"id": str(n["_id"]), "type": n["type"], "message_key": f"dashboard.notif.{n['type']}",
                           "params": n.get("params", {}), "read": bool(n.get("read")),
                           "created_at": to_json(n.get("created_at"))} for n in notes],
    }


def _aware(d):
    if not isinstance(d, datetime):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _first(docs, *fields):
    """Earliest real timestamp across the given fields of the docs (None when there is none)."""
    return min((x for d in docs for f in fields if (x := _aware(d.get(f)))), default=None)


@router.get("/dashboard/impact")
async def impact(user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    signup = _aware(user.get("created_at"))
    reset = _aware(company.get("demo_reset_at")) if company.get("is_demo_company") else None
    start, measured_from = (reset, "demo_reset") if reset else (signup, "signup")
    pids = [str(p["_id"]) async for p in db.products.find({"company_id": cid})]
    sf = _first(await db.storefronts.find({"company_id": cid}).to_list(50), "first_published_at", "published_at")
    rep = _first(await db.readiness_reports.find({"product_id": {"$in": pids}}).to_list(500), "created_at") if pids else None
    out = _first(await db.messages.find({"company_id": cid, "direction": "outbound", "status": "sent",
                                         "kind": {"$in": ["cold", "rfq_answer"]}}).to_list(5000), "approved_at")
    dur = lambda t: int((t - start).total_seconds()) if t and start and t >= start else None  # noqa: E731
    return {"signup_at": to_json(signup), "measured_from": measured_from, "measured_from_at": to_json(start),
            "storefront_published_at": to_json(sf), "first_report_at": to_json(rep),
            "first_approved_outreach_at": to_json(out),
            "durations_s": {"to_storefront": dur(sf), "to_report": dur(rep), "to_outreach": dur(out)}}


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, company: dict = Depends(current_company)):
    n = await owned("notifications", notification_id, str(company["_id"]))
    await get_db().notifications.update_one({"_id": n["_id"]}, {"$set": {"read": True}})
    return {"id": notification_id, "read": True}
