from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import current_company, current_user, owned
from app.core.serialize import to_json
from app.models.compliance import GtipConfirmIn, GtipIn
from app.services import agent_steps, regai_service as regai

router = APIRouter(prefix="/compliance")


@router.post("/gtip")
async def gtip(body: GtipIn, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    product = await owned("products", body.product_id, cid)
    job_id = await agent_steps.create_job(db, cid, "gtip", ["gtip"])
    ui = user.get("ui_language", "tr")
    # a re-run means re-classify: drop the old confirmation so product and classification agree
    await db.products.update_one({"_id": product["_id"]}, {"$set": {"hs_code_confirmed": None}})

    async def run():
        cands = [c.model_dump() for c in await regai.suggest_gtip(product, company, body.processing, ui, job_id)]
        doc = {"company_id": cid, "product_id": body.product_id, "candidates": cands, "processing": body.processing,
               "confirmed_code": None, "confirmed_at": None, "created_at": datetime.now(timezone.utc)}
        await db.classifications.replace_one({"product_id": body.product_id}, doc, upsert=True)
        await agent_steps.finish_job(job_id, {"candidates": cands, "processing": body.processing})

    agent_steps.spawn(run(), job_id)
    return {"job_id": job_id}


@router.get("/gtip")
async def get_gtip(product_id: str, company: dict = Depends(current_company)):
    await owned("products", product_id, str(company["_id"]))
    doc = await get_db().classifications.find_one({"product_id": product_id})
    if not doc:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return to_json(doc)


@router.post("/gtip/confirm")
async def confirm(body: GtipConfirmIn, company: dict = Depends(current_company)):
    db = get_db()
    product = await owned("products", body.product_id, str(company["_id"]))
    code = regai.normalize_hs6(body.code)
    doc = await db.classifications.find_one({"product_id": body.product_id}) or {}
    known = code and (code in {c["code"] for c in doc.get("candidates", [])}
                      or await db.kb_hs_codes.find_one({"id": code}))
    if not known:
        raise HTTPException(422, {"code": "unknown_hs_code", "message_key": "errors.unknown_hs_code"})
    now = datetime.now(timezone.utc)
    await db.classifications.update_one(
        {"product_id": body.product_id},
        {"$set": {"confirmed_code": code, "confirmed_at": now},
         "$setOnInsert": {"company_id": str(company["_id"]), "candidates": [], "processing": None, "created_at": now}},
        upsert=True)
    await db.products.update_one({"_id": product["_id"]}, {"$set": {"hs_code_confirmed": code}})
    return to_json(await db.classifications.find_one({"product_id": body.product_id}))
