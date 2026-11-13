from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import current_company, owned
from app.core.serialize import to_json

router = APIRouter()


def _ts(doc: dict) -> datetime:
    d = doc.get("created_at")
    if not isinstance(d, datetime):
        return datetime.min.replace(tzinfo=timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


@router.get("/dashboard")
async def dashboard(company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    products = await db.products.find({"company_id": cid}).to_list(500)
    pids = [str(p["_id"]) for p in products]
    market = await db.markets.find_one({"company_id": cid})
    sfs = await db.storefronts.find({"company_id": cid}).to_list(50)
    sf = next((s for s in sfs if s.get("status") == "published"), sfs[0] if sfs else None)
    report = None
    if pids:  # newest report across all the company's products
        reports = await db.readiness_reports.find({"product_id": {"$in": pids}}).to_list(500)
        report = max(reports, key=_ts, default=None)
    leads = await db.leads.find({"company_id": cid}).to_list(5000)
    lids = [str(x["_id"]) for x in leads]
    pending = sent_quote = 0
    if lids:
        pending = await db.messages.count_documents({"lead_id": {"$in": lids}, "status": "draft"})
        pending += await db.quotes.count_documents({"lead_id": {"$in": lids}, "status": "draft"})
        sent_quote = await db.quotes.count_documents({"lead_id": {"$in": lids}, "status": "sent"})
    notes = await db.notifications.find({"company_id": cid}).to_list(200)
    notes.sort(key=_ts, reverse=True)
    return {
        "company": {"name": company["name"], "country_code": (market or {}).get("country_code", "DE")},
        "storefront": {"status": sf["status"] if sf else "none", "slug": sf.get("slug") if sf else None},
        "compliance": {"score": report.get("score") if report else None},
        "leads": {"count": len(leads), "pending_approvals": pending},
        "roadmap": {"profile": bool(products), "storefront": bool(sf and sf["status"] == "published"),
                    "compliance": report is not None, "first_quote": sent_quote > 0},
        "notifications": [{"id": str(n["_id"]), "type": n["type"], "message_key": f"dashboard.notif.{n['type']}",
                           "params": n.get("params", {}), "read": bool(n.get("read")),
                           "created_at": to_json(n.get("created_at"))} for n in notes[:20]],
    }


@router.post("/notifications/{notification_id}/read")
async def mark_read(notification_id: str, company: dict = Depends(current_company)):
    n = await owned("notifications", notification_id, str(company["_id"]))
    await get_db().notifications.update_one({"_id": n["_id"]}, {"$set": {"read": True}})
    return {"id": notification_id, "read": True}
