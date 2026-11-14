import re
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator

from app.core.db import get_db
from app.core.ratelimit import RateLimiter

router = APIRouter(prefix="/public")
_limiter = RateLimiter(5, 3600)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class RfqIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=120)
    contact_name: str = Field(min_length=1, max_length=120)
    email: str = Field(max_length=254)
    country: str = Field(pattern=r"^[A-Z]{2}$")
    products: list[str] = Field(default_factory=list, max_length=10)
    quantity: str = Field(default="", max_length=120)
    message: str = Field(max_length=2000)
    gdpr_consent: bool
    website_hp: str = Field(default="", max_length=500)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        if not _EMAIL.match(v):
            raise ValueError("invalid_email")
        return v

    @field_validator("products")
    @classmethod
    def _products(cls, v: list[str]) -> list[str]:
        if any(len(p) > 120 for p in v):
            raise ValueError("product_too_long")
        return v

    @field_validator("gdpr_consent")
    @classmethod
    def _gdpr(cls, v: bool) -> bool:
        if not v:
            raise ValueError("gdpr_required")
        return v


async def _published(slug: str) -> dict:
    doc = await get_db().storefronts.find_one({"slug": slug, "status": "published"})
    if not doc:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return doc


async def _company(doc: dict) -> dict:
    return await get_db().companies.find_one({"_id": ObjectId(doc["company_id"])}) or {}


@router.get("/storefronts/{slug}")
async def get_storefront(slug: str):
    doc = await _published(slug)
    co, cfg = await _company(doc), doc["site_config"]
    contact = co.get("contact") or {}
    pub_contact = {k: contact.get(k) for k in ("phone", "email", "website")}
    return {  # explicit allow-list: never serialize the raw docs
        "slug": doc["slug"],
        "site_config": {"de": cfg.get("de"), "en": cfg.get("en"), "template": cfg.get("template")},
        "company": {"name": co.get("name"), "city": co.get("city"), "logo_url": co.get("logo_url"),
                    "contact": pub_contact, "founded_year": co.get("founded_year")},
        "legal": {"name": co.get("name"), "address": co.get("city"), **pub_contact,
                  "representative": None, "register": None},
    }


@router.post("/storefronts/{slug}/rfq")
async def rfq(slug: str, body: RfqIn, request: Request):
    doc = await _published(slug)
    if body.website_hp:
        return Response(status_code=204)  # bot: pretend success, store nothing
    _limiter.check(f"{request.client.host if request.client else '-'}|{slug}")
    db, now = get_db(), datetime.now(timezone.utc)
    cid = doc["company_id"]
    await db.leads.insert_one({
        "company_id": cid, "source": "rfq", "company_name": body.company_name, "country": body.country,
        "contact_name": body.contact_name, "email": body.email, "website": None, "notes": body.message,
        "score": 0, "status": "new", "is_demo": False, "is_hot": True, "products_of_interest": body.products,
        "quantity": body.quantity, "source_note": f"RFQ /s/{slug}", "created_at": now})
    await db.notifications.insert_one({
        "company_id": cid, "type": "rfq", "params": {"company": body.company_name},
        "message_tr": f"Yeni teklif talebi: {body.company_name}", "read": False, "created_at": now})
    return Response(status_code=201)
