from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import require_admin
from app.models.admin import PingOut
from app.services.llm_service import generate_json

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.post("/llm-test", response_model=PingOut)
async def llm_test():
    return await generate_json("admin_ping", {}, PingOut, run_type="llm_test", company_id=None)


async def _counts(db, demo_ids: list[str]) -> dict:
    """Counts only. demo_ids are company ids to leave out (empty = everything)."""
    by_co = {"company_id": {"$nin": demo_ids}}
    demo_pids = [str(p["_id"]) async for p in db.products.find({"company_id": {"$in": demo_ids}})] if demo_ids else []
    return {
        "companies": await db.companies.count_documents({"is_demo_company": {"$ne": True}} if demo_ids else {}),
        "storefronts_published": await db.storefronts.count_documents({**by_co, "status": "published"}),
        "reports": await db.readiness_reports.count_documents({"product_id": {"$nin": demo_pids}}),
        "approved_messages": await db.messages.count_documents({**by_co, "direction": "outbound", "status": "sent"}),
        "rfqs": await db.leads.count_documents({**by_co, "source": "rfq"}),
    }


@router.get("/stats")
async def stats():
    db = get_db()
    demo_ids = [str(c["_id"]) async for c in db.companies.find({"is_demo_company": True})]
    return {**await _counts(db, []), "excluding_demo": await _counts(db, demo_ids)}
