import logging
import time
from datetime import datetime, timezone

from bson import ObjectId

from app.models.company import CompanyIn
from app.models.product import ProductIn
from app.seed import DEMO_LEAD_NOTE, _load, _names, backfill_seed_keys
from app.seed.images import make_placeholder
from app.services.storage_service import get_storage
from app.services.agent_steps import spawn
from app.services.llm_service import generate_text
from app.services.scoring import score_for_company

from app.services.upload_registry import record_upload  # noqa: E402

log = logging.getLogger(__name__)
# demo key -> seed company key; looked up by the seeded company name, never by ObjectId
DEMO_KEYS = {"gaziantep": "bozkurt", "denizli": "pamukkale", "bursa": "uludag"}
ACTIVITY = ("storefronts", "classifications", "readiness_reports", "messages", "quotes", "tasks", "notifications",
            "jobs", "lead_imports")


def _spec(key: str) -> dict:
    return next(s for s in _load("companies") if s["key"] == DEMO_KEYS[key])


async def _find(db, key: str) -> tuple[dict, dict] | None:
    spec = _spec(key)
    company = await db.companies.find_one({"name": spec["company"]["name"], "is_demo_company": True})
    return (spec, company) if company else None


async def list_demo_companies(db) -> list[dict]:
    out = []
    for key in DEMO_KEYS:
        spec = _spec(key)
        if await db.companies.find_one({"name": spec["company"]["name"], "is_demo_company": True}):
            out.append({"key": key, "name": spec["company"]["name"], "email": spec["user"]["email"]})
    return out


async def _warmup(cid: str) -> None:
    try:
        await generate_text("admin_ping", {}, run_type="warmup", company_id=cid)
    except Exception as e:  # no key / provider down: the demo still works from the cache
        log.warning("demo warm-up skipped: %s", e)


async def reset_demo_company(db, key: str) -> dict | None:
    """Back to the clean seed state, same ids (so demo_cache keys stay valid). None if the company is not seeded."""
    t0 = time.monotonic()
    found = await _find(db, key)
    if not found:
        return None
    spec, company = found
    cid = str(company["_id"])
    for coll in ACTIVITY:
        await db[coll].delete_many({"company_id": cid})
    await db.leads.delete_many({"company_id": cid, "is_demo": {"$ne": True}})
    await db.companies.update_one({"_id": company["_id"]}, {"$set": {**CompanyIn(**spec["company"]).model_dump(),
                                                                       "storefront_slug": spec["company"].get("storefront_slug"),
                                                                       "demo_reset_at": datetime.now(timezone.utc)}})
    await backfill_seed_keys(db, cid, spec)
    keys = [f"{spec['key']}:{i}" for i in range(len(spec["products"]))]
    await db.products.delete_many({"company_id": cid, "seed_key": {"$nin": keys}})  # products the producer added
    now = datetime.now(timezone.utc)
    for key_, p in zip(keys, spec["products"]):
        old = await db.products.find_one({"company_id": cid, "seed_key": key_}) or {}
        photos = old.get("seed_photos") or old.get("photos") or [
            await get_storage().save(make_placeholder(label, spec["color"]), "products")
            for label in p["photo_labels"]]  # the product was deleted: regenerate its placeholders
        body = ProductIn(**{k: v for k, v in p.items() if k != "photo_labels"}, photos=photos).model_dump()
        for url in photos:
            await record_upload(db, url, company["owner_id"])
        await db.products.update_one({"company_id": cid, "seed_key": key_},
                                     {"$set": {**body, "hs_code_confirmed": None, "seed_photos": photos, **_names(p)},
                                      "$setOnInsert": {"created_at": now}}, upsert=True)
    company = await db.companies.find_one({"_id": company["_id"]})
    for lead in _load("demo_leads")[spec["key"]]:
        doc = {**lead, "company_id": cid, "source": "demo", "country": "DE", "is_demo": True,
               "source_note": DEMO_LEAD_NOTE, "status": "new", "created_at": now}
        sc = await score_for_company(db, company, doc)
        await db.leads.replace_one({"company_id": cid, "email": lead["email"]},
                                   {**doc, "score": sc["total"], "score_breakdown": sc["breakdown"]}, upsert=True)
    # warm the LLM connection for the demo; not awaited, failures are logged by spawn
    spawn(_warmup(cid))
    return {"elapsed_ms": int((time.monotonic() - t0) * 1000)}
