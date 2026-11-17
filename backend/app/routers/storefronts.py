import io

from datetime import datetime, timezone

import qrcode
from fastapi import APIRouter, Depends, HTTPException, Response

from app.core.config import get_settings

from app.core.db import get_db
from app.core.security import current_company, current_user
from app.core.serialize import to_json
from app.models.storefront import IntakeIn, RegenIn, SiteConfig, SiteConfigIn
from app.services import agent_steps, storefront_service as sf

router = APIRouter(prefix="/storefronts")


def _err(status: int, code: str):
    return HTTPException(status, {"code": code, "message_key": f"errors.{code}"})


async def _mine(company: dict) -> dict:
    doc = await get_db().storefronts.find_one({"company_id": str(company["_id"]), "country": "DE"})
    if not doc:
        raise _err(404, "not_found")
    return doc


@router.post("/generate")
async def generate(body: IntakeIn, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db = get_db()
    job_id = await agent_steps.create_job(db, str(company["_id"]), "storefront",
                                          ["analysis", "adaptation", "content", "theme"])
    ui = user.get("ui_language", "tr")

    async def run():
        products = await db.products.find({"company_id": str(company["_id"])}).to_list(50)
        cfg = await sf.generate_site_config(job_id, company, products, body, ui)
        doc = await sf.save_generated(db, company, cfg)
        await agent_steps.finish_job(job_id, {"storefront_id": str(doc["_id"]), "slug": doc["slug"]})

    agent_steps.spawn(run(), job_id)
    return {"job_id": job_id}


@router.get("/mine")
async def get_mine(company: dict = Depends(current_company)):
    return to_json(await _mine(company))


@router.put("/mine")
async def put_mine(body: SiteConfigIn, company: dict = Depends(current_company)):
    doc = await _mine(company)
    slug = sf.slugify_tr(body.slug)
    if slug != doc["slug"] and await get_db().storefronts.find_one({"slug": slug, "_id": {"$ne": doc["_id"]}}):
        raise _err(409, "slug_taken")
    cfg = body.site_config.model_copy(update={"template": body.template})
    cfg.missing = sf.compute_missing(cfg)  # never trust the client's list
    patch = {"site_config": cfg.model_dump(), "template": body.template, "slug": slug,
             "updated_at": datetime.now(timezone.utc)}
    await get_db().storefronts.update_one({"_id": doc["_id"]}, {"$set": patch})
    return to_json({**doc, **patch})


@router.post("/mine/regenerate-section")
async def regenerate(body: RegenIn, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    db, doc = get_db(), await _mine(company)
    cfg = SiteConfig.model_validate(doc["site_config"])
    products = await db.products.find({"company_id": str(company["_id"])}).to_list(50)
    section, fallback, source = await sf.regenerate_section(company, products, cfg, body.section, body.lang,
                                                    body.instruction, user.get("ui_language", "tr"))
    if not fallback:
        data = cfg.model_dump()
        data[body.lang][body.section] = section
        cfg = SiteConfig.model_validate(data)
        cfg.missing = sf.compute_missing(cfg)
        await db.storefronts.update_one({"_id": doc["_id"]}, {"$set": {"site_config": cfg.model_dump()}})
    return {"section": section, "fallback": fallback, "source": source, "missing": cfg.missing}


async def _set_status(company: dict, status: str, stamp: str) -> dict:
    doc = await _mine(company)
    now = datetime.now(timezone.utc)
    patch = {"status": status, stamp: now}
    await get_db().storefronts.update_one({"_id": doc["_id"]}, {"$set": patch})
    if status == "published" and not doc.get("first_published_at"):  # set once, survives republish
        await get_db().storefronts.update_one({"_id": doc["_id"]}, {"$set": {"first_published_at": now}})
        patch["first_published_at"] = now
    return to_json({**doc, **patch})


@router.post("/mine/publish")
async def publish(company: dict = Depends(current_company)):
    return await _set_status(company, "published", "published_at")


@router.post("/mine/unpublish")
async def unpublish(company: dict = Depends(current_company)):
    return await _set_status(company, "draft", "unpublished_at")


@router.get("/mine/qr.png")
async def qr_png(company: dict = Depends(current_company)):
    doc = await _mine(company)
    buf = io.BytesIO()
    qrcode.make(f"{get_settings().frontend_origin}/s/{doc['slug']}").save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")


@router.get("/mine/impressum-checklist")
async def impressum_checklist(company: dict = Depends(current_company)):
    c = company.get("contact") or {}
    have = {"name": company.get("name"), "address": company.get("city"), "phone": c.get("phone"),
            "email": c.get("email"), "representative": None, "register": None}  # not collected yet: always to-check
    return [{"field": k, "present": bool(v)} for k, v in have.items()]
