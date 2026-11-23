import json
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId

from app.core.config import get_settings
from app.core.db import ensure_indexes
from app.core.security import hash_password
from app.models.company import CompanyIn
from app.models.product import ProductIn
from app.services.scoring import score_for_company
from app.seed.images import demo_photo
from app.services.storage_service import get_storage
from app.services.upload_registry import record_upload

DATA = Path(__file__).parent / "data"
DEMO_LEAD_NOTE = "DEMO – kurgusal firma"


def _load(name: str):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


async def _upsert_kb(coll, records: list[dict]) -> None:
    for rec in records:
        # verified/last_verified only on insert so a re-run never undoes an admin's verification
        await coll.update_one({"id": rec["id"]}, {"$set": rec, "$setOnInsert": {"verified": False, "last_verified": None}},
                              upsert=True)


async def _ensure_user(db, email: str, name: str, password: str, is_admin: bool, now) -> str:
    user = await db.users.find_one({"email": email})
    if user:
        return str(user["_id"])
    doc = {"email": email, "password_hash": hash_password(password), "name": name, "is_admin": is_admin,
           "ui_language": "tr", "created_at": now, "kvkk_consent_at": now}
    return str((await db.users.insert_one(doc)).inserted_id)


async def backfill_seed_keys(db, cid: str, spec: dict) -> None:
    """Give every seeded product a stable seed_key (and seed_photos). Legacy docs match by original name,
    leftovers by creation order, so a product renamed before the key existed is still recognised."""
    keys = [f"{spec['key']}:{i}" for i in range(len(spec["products"]))]
    docs = await db.products.find({"company_id": cid}).sort("_id", 1).to_list(500)
    have = {d["seed_key"] for d in docs if d.get("seed_key") in keys}
    free = [k for k in keys if k not in have]
    for d in docs:
        if d.get("seed_key") in keys:
            continue
        i = next((i for i, p in enumerate(spec["products"]) if p["name_tr"] == d["name_tr"]
                  and keys[i] in free), None)
        if i is not None:
            free.remove(keys[i])
            await db.products.update_one({"_id": d["_id"]}, {"$set": {"seed_key": keys[i]}})
            d["seed_key"] = keys[i]
    for d in docs:
        if d.get("seed_key") not in keys and free:
            d["seed_key"] = free.pop(0)
            await db.products.update_one({"_id": d["_id"]}, {"$set": {"seed_key": d["seed_key"]}})
    for d in docs:
        if d.get("seed_key") in keys and not d.get("seed_photos"):
            await db.products.update_one({"_id": d["_id"]}, {"$set": {"seed_photos": d.get("photos") or []}})


def _names(p: dict) -> dict:
    """Demo-only buyer-language product names (not part of ProductIn): keep the fallback storefront demo-ready."""
    return {k: p[k] for k in ("name_de", "name_en") if p.get(k)}


async def _seed_company(db, spec: dict, password: str, now) -> str:
    owner = await _ensure_user(db, spec["user"]["email"], spec["user"]["name"], password, False, now)
    fields = CompanyIn(**spec["company"]).model_dump()  # same model the API validates with
    await db.companies.update_one({"owner_id": owner}, {"$set": {**fields, "is_demo_company": True,
                                                  "storefront_slug": spec["company"].get("storefront_slug")},
                                  "$setOnInsert": {"created_at": now}}, upsert=True)
    cid = str((await db.companies.find_one({"owner_id": owner}))["_id"])
    await backfill_seed_keys(db, cid, spec)
    for i, p in enumerate(spec["products"]):
        existing = await db.products.find_one({"company_id": cid, "seed_key": f"{spec['key']}:{i}"})
        if existing:
            continue  # keeps photos and any edits; no new files on re-run
        photos = [await get_storage().save(demo_photo(spec["key"], label, spec["color"]), "products")
                  for label in p["photo_labels"]]
        body = ProductIn(**{k: v for k, v in p.items() if k != "photo_labels"}, photos=photos)
        await db.products.insert_one({**body.model_dump(), "company_id": cid, "hs_code_confirmed": None,
                                      "seed_photos": photos, "seed_key": f"{spec['key']}:{i}", "created_at": now,
                                      **_names(p)})
    for p in await db.products.find({"company_id": cid}).to_list(500):  # also backfills pre-registry seeds
        for url in p.get("photos") or []:
            await record_upload(db, url, owner)
    if fields.get("logo_url"):
        await record_upload(db, fields["logo_url"], owner)
    await db.markets.update_one({"company_id": cid}, {"$setOnInsert": {"country_code": "DE", "languages": ["de", "en"],
                                "status": "active"}}, upsert=True)
    return cid


async def seed(db) -> dict[str, int]:
    s = get_settings()
    if not s.seed_password:
        raise RuntimeError("SEED_PASSWORD is not set; refusing to seed demo accounts")
    await ensure_indexes(db)
    # leads stored before is_hot existed would sort below every manual lead (missing < false)
    await db.leads.update_many({"is_hot": {"$exists": False}}, {"$set": {"is_hot": False}})
    now = datetime.now(timezone.utc)
    await _ensure_user(db, (s.admin_email or "admin@kobi-gpt.local").strip().lower(), "Admin", s.seed_password, True, now)
    leads = _load("demo_leads")
    for spec in _load("companies"):
        cid = await _seed_company(db, spec, s.seed_password, now)
        company = await db.companies.find_one({"_id": ObjectId(cid)})
        for lead in leads[spec["key"]]:
            doc = {"is_hot": False, **lead, "company_id": cid, "source": "demo", "country": "DE", "is_demo": True,
                   "source_note": DEMO_LEAD_NOTE}
            sc = await score_for_company(db, company, doc)
            await db.leads.update_one(
                {"company_id": cid, "email": lead["email"]},
                {"$set": {**doc, "score": sc["total"], "score_breakdown": sc["breakdown"]},
                 "$setOnInsert": {"created_at": now, "status": "new"}},  # keeps status across re-seeds
                upsert=True)
    await _upsert_kb(db.kb_rules, _load("kb_rules"))
    await _upsert_kb(db.kb_incentives, _load("kb_incentives"))
    await _upsert_kb(db.kb_hs_codes, _load("kb_hs_codes"))
    for rate in _load("logistics_rates"):
        await db.logistics_rates.update_one({"key": rate["key"]}, {"$set": rate}, upsert=True)
    names = ["users", "companies", "products", "markets", "leads", "kb_rules", "kb_incentives", "kb_hs_codes",
             "logistics_rates"]
    return {n: await db[n].count_documents({}) for n in names}
