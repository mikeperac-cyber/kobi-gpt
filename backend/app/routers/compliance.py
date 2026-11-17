from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.db import get_db
from app.services.upload_registry import record_upload
from app.core.security import current_company, current_user, owned
from app.core.serialize import to_json
from app.models.compliance import CheckIn, GtipConfirmIn, GtipIn, TickIn
from app.services import agent_steps, regai_service as regai
from app.services.pdf_service import STRINGS, readiness_pdf
from app.services.storage_service import get_storage

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


@router.post("/check")
async def check(body: CheckIn, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    product = await owned("products", body.product_id, cid)
    if not product.get("hs_code_confirmed"):
        raise HTTPException(409, {"code": "gtip_not_confirmed", "message_key": "errors.gtip_not_confirmed"})
    market = await db.markets.find_one({"company_id": cid}) or {}
    country, ui = (market.get("country_code") or "DE").upper(), user.get("ui_language", "tr")
    job_id = await agent_steps.create_job(db, cid, "compliance", ["rules", "incentives", "next_steps"])

    async def run():
        doc = await regai.build_report(product, company, country=country, channel=body.channel,
                                       structural_use=body.structural_use, ui=ui, job_id=job_id)
        doc["created_at"] = datetime.now(timezone.utc)
        rid = str((await db.readiness_reports.insert_one(doc)).inserted_id)
        await agent_steps.finish_job(job_id, {"report_id": rid})

    agent_steps.spawn(run(), job_id)
    return {"job_id": job_id}


@router.get("/reports/latest")
async def latest_report(product_id: str, company: dict = Depends(current_company)):
    await owned("products", product_id, str(company["_id"]))
    docs = await get_db().readiness_reports.find({"product_id": product_id}).sort("created_at", -1).to_list(1)
    if not docs:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return to_json(await regai.refresh_verification(get_db(), docs[0]))


@router.patch("/reports/{report_id}/items/{rule_id}")
async def tick(report_id: str, rule_id: str, body: TickIn, company: dict = Depends(current_company)):
    rep = await owned("readiness_reports", report_id, str(company["_id"]))
    if rule_id not in {i["rule_id"] for i in rep["checklist"]}:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    db = get_db()
    # positional update so concurrent ticks on different items cannot overwrite each other
    await db.readiness_reports.update_one({"_id": rep["_id"], "checklist.rule_id": rule_id},
                                          {"$set": {"checklist.$.done": body.done}})
    fresh = await db.readiness_reports.find_one({"_id": rep["_id"]})
    score = regai.readiness_score(fresh["checklist"])
    await db.readiness_reports.update_one({"_id": rep["_id"]}, {"$set": {"score": score}})
    return {"score": score}


@router.post("/reports/{report_id}/next-steps")
async def refresh_next_steps(report_id: str, user: dict = Depends(current_user),
                             company: dict = Depends(current_company)):
    db = get_db()
    rep = await owned("readiness_reports", report_id, str(company["_id"]))
    kb = {r["id"]: r for r in await db.kb_rules.find({}).to_list(500)}
    steps = await regai.next_steps(rep["checklist"], kb, company, user.get("ui_language", "tr"), None,
                                 rep["product_id"])
    await db.readiness_reports.update_one({"_id": rep["_id"]}, {"$set": {"next_steps": steps}})
    return {"next_steps": steps}


@router.get("/reports/{report_id}/pdf")
async def report_pdf(report_id: str, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db, lang = get_db(), user.get("ui_language", "tr")
    rep = await owned("readiness_reports", report_id, str(company["_id"]))
    product = await db.products.find_one({"_id": ObjectId(rep["product_id"])}) or {}
    contact = company.get("contact") or {}
    public = {"name": company.get("name"), "city": company.get("city"), "sector": company.get("sector"),
              "contact": {k: contact.get(k) for k in ("email", "phone", "website")}}  # allow-list, never a product doc
    data = readiness_pdf({**to_json(await regai.refresh_verification(db, rep)), "product_name": product.get("name_tr", "")}, public, lang)
    url = await get_storage().save_file(data, f"reports/{company['_id']}", ".pdf")
    await record_upload(db, url, company["owner_id"])
    await db.readiness_reports.update_one({"_id": rep["_id"]}, {"$set": {"pdf_url": url}})
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{STRINGS[lang]["file"]}"'})
