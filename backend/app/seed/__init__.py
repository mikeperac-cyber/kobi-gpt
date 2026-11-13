import json
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import get_settings
from app.core.db import ensure_indexes
from app.core.security import hash_password
from app.models.company import CompanyIn
from app.models.product import ProductIn
from app.seed.images import make_placeholder
from app.services.storage_service import get_storage

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


async def _seed_company(db, spec: dict, password: str, now) -> str:
    owner = await _ensure_user(db, spec["user"]["email"], spec["user"]["name"], password, False, now)
    fields = CompanyIn(**spec["company"]).model_dump()  # same model the API validates with
    await db.companies.update_one({"owner_id": owner}, {"$set": {**fields, "is_demo_company": True},
                                  "$setOnInsert": {"created_at": now}}, upsert=True)
    cid = str((await db.companies.find_one({"owner_id": owner}))["_id"])
    for p in spec["products"]:
        existing = await db.products.find_one({"company_id": cid, "name_tr": p["name_tr"]})
        if existing:
            continue  # keeps photos and any edits; no new files on re-run
        photos = [await get_storage().save(make_placeholder(label, spec["color"]), "products")
                  for label in p["photo_labels"]]
        body = ProductIn(**{k: v for k, v in p.items() if k != "photo_labels"}, photos=photos)
        await db.products.insert_one({**body.model_dump(), "company_id": cid, "hs_code_confirmed": None,
                                      "created_at": now})
    await db.markets.update_one({"company_id": cid}, {"$setOnInsert": {"country_code": "DE", "languages": ["de", "en"],
                                "status": "active"}}, upsert=True)
    return cid


async def seed(db) -> dict[str, int]:
    s = get_settings()
    if not s.seed_password:
        raise RuntimeError("SEED_PASSWORD is not set; refusing to seed demo accounts")
    await ensure_indexes(db)
    now = datetime.now(timezone.utc)
    await _ensure_user(db, (s.admin_email or "admin@kobi-gpt.local").strip().lower(), "Admin", s.seed_password, True, now)
    leads = _load("demo_leads")
    for spec in _load("companies"):
        cid = await _seed_company(db, spec, s.seed_password, now)
        for lead in leads[spec["key"]]:
            await db.leads.update_one(
                {"company_id": cid, "email": lead["email"]},
                {"$set": {**lead, "company_id": cid, "source": "demo", "country": "DE", "score": 0, "status": "new",
                          "is_demo": True, "source_note": DEMO_LEAD_NOTE}, "$setOnInsert": {"created_at": now}},
                upsert=True)
    await _upsert_kb(db.kb_rules, _load("kb_rules"))
    await _upsert_kb(db.kb_incentives, _load("kb_incentives"))
    await _upsert_kb(db.kb_hs_codes, _load("kb_hs_codes"))
    for rate in _load("logistics_rates"):
        await db.logistics_rates.update_one({"key": rate["key"]}, {"$set": rate}, upsert=True)
    names = ["users", "companies", "products", "markets", "leads", "kb_rules", "kb_incentives", "kb_hs_codes",
             "logistics_rates"]
    return {n: await db[n].count_documents({}) for n in names}
