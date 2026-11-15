from bson import ObjectId
from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import current_company, current_user, owned
from app.core.serialize import to_json
from app.models.message import DraftIn, MessageEditIn, RejectIn
from app.services import outreach_service as svc

router = APIRouter()


async def _products(cid: str) -> list[dict]:
    return await get_db().products.find({"company_id": cid}).to_list(100)


@router.post("/leads/{lead_id}/draft", status_code=201)
async def draft(lead_id: str, body: DraftIn, company: dict = Depends(current_company),
                user: dict = Depends(current_user)):
    cid = str(company["_id"])
    lead = await owned("leads", lead_id, cid)
    if lead["status"] == "do_not_contact":
        raise svc.err(409, "do_not_contact")
    sf = await get_db().storefronts.find_one({"company_id": cid, "status": "published"})
    url = f"{get_settings().frontend_origin}/s/{sf['slug']}" if sf and sf.get("slug") else None
    msg = await svc.draft_first_contact(lead, company, await _products(cid), url, body.tone,
                                        user.get("ui_language", "tr"))
    return to_json(msg)


@router.put("/messages/{message_id}")
async def edit(message_id: str, body: MessageEditIn, company: dict = Depends(current_company),
               user: dict = Depends(current_user)):
    cid = str(company["_id"])
    msg = await owned("messages", message_id, cid)
    return to_json(await svc.edit_message(msg, body.subject, body.body, company, await _products(cid),
                                          user.get("ui_language", "tr")))


@router.post("/messages/{message_id}/approve")
async def approve(message_id: str, company: dict = Depends(current_company), user: dict = Depends(current_user)):
    msg = await owned("messages", message_id, str(company["_id"]))
    return to_json(await svc.approve_and_send(get_db(), msg["_id"], user))


@router.post("/messages/{message_id}/reject")
async def reject(message_id: str, body: RejectIn, company: dict = Depends(current_company)):
    msg = await owned("messages", message_id, str(company["_id"]))
    if msg["status"] != "draft":
        raise svc.err(409, "not_draft")
    upd = {"status": "rejected", "reject_reason": body.reason.strip()}
    await get_db().messages.update_one({"_id": msg["_id"]}, {"$set": upd})
    db = get_db()  # lead goes back to "new" if this was its only draft
    if not await db.messages.count_documents({"lead_id": msg["lead_id"], "status": "draft"}):
        await db.leads.update_one({"_id": ObjectId(msg["lead_id"]), "status": "draft_ready"},
                                  {"$set": {"status": "new"}})
    return to_json({**msg, **upd})


@router.get("/approvals")
async def approvals(company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    drafts = await db.messages.find({"company_id": cid, "status": "draft"}).to_list(500)
    drafts.sort(key=lambda m: m["created_at"].timestamp(), reverse=True)
    leads = {str(x["_id"]): x async for x in db.leads.find({"company_id": cid})}
    for m in drafts:
        lead = leads.get(m["lead_id"], {})
        m["lead"] = {"company_name": lead.get("company_name"), "email": lead.get("email"),
                     "country": lead.get("country"), "is_demo": bool(lead.get("is_demo"))}
    return {"messages": to_json(drafts), "quotes": []}  # quotes arrive in Task 28
