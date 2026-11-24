import html
import json
from datetime import datetime, timezone
from typing import Literal

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from app.core.config import get_settings
from app.core.db import get_db
from app.core.ratelimit import RateLimiter
from app.core.text import EMAIL as _EMAIL
from app.core.clock import tr_today
from app.services.scoring import score_for_company
from app.services.verification_service import public_trust

router = APIRouter(prefix="/public")
_limiter = RateLimiter(5, 3600)
_demo_limiter = RateLimiter(30, 3600)  # a jury on one venue Wi-Fi shares an IP; demo data is throwaway


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
                    "contact": pub_contact, "founded_year": co.get("founded_year"),
                    # a judge must never dial an invented seed number: demo companies use the presenter's phone
                    "whatsapp": (get_settings().demo_whatsapp_phone or None) if co.get("is_demo_company")
                    else contact.get("phone"),
                    "trust": await public_trust(get_db(), co, tr_today())},
        "legal": {"name": co.get("name"), "address": co.get("city"), **pub_contact,
                  "representative": None, "register": None},
    }


_LOCALE = {"de": "de_DE", "en": "en_GB"}


@router.get("/storefronts/{slug}/share", response_class=HTMLResponse)
async def share_page(slug: str, lang: Literal["de", "en"] = "de"):
    """Link-preview page for chat apps and crawlers (they do not run the React app); humans are sent on."""
    doc = await _published(slug)
    co, c = await _company(doc), doc["site_config"].get(lang) or {}
    origin = get_settings().frontend_origin.rstrip("/")
    url = f"{origin}/s/{slug}"
    seo, hero = c.get("seo") or {}, c.get("hero") or {}
    title = seo.get("title") or co.get("name") or slug  # same fallbacks as PublicStorefront.useHead
    desc = seo.get("description") or hero.get("subheadline") or ""
    img = next((ph[0] for ph in ((pr.get("photos") or []) for pr in c.get("products") or []) if ph), None)
    img = img or co.get("logo_url")
    org = {"@context": "https://schema.org", "@type": "Organization", "name": co.get("name"), "url": url,
           "address": {"@type": "PostalAddress", "addressLocality": co.get("city")}}
    if co.get("logo_url"):
        org["logo"] = origin + co["logo_url"]
    e = lambda v: html.escape(str(v), quote=True)  # noqa: E731
    meta = [("name", "description", desc), ("property", "og:type", "website"), ("property", "og:title", title),
            ("property", "og:description", desc), ("property", "og:url", url), ("property", "og:locale", _LOCALE[lang]),
            ("name", "twitter:card", "summary_large_image"), ("name", "twitter:title", title)]
    if img:
        meta.append(("property", "og:image", origin + img))
    ld = json.dumps(org, ensure_ascii=False).replace("<", "\\u003c").replace(">", "\\u003e")  # no "</script>" inside the block
    page = (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{e(title)}</title>'
            + "".join(f'<meta {a}="{k}" content="{e(v)}">' for a, k, v in meta)
            + f'<link rel="canonical" href="{e(url)}">'
            + f'<script type="application/ld+json">{ld}</script>'
            + f'<meta http-equiv="refresh" content="0;url=/s/{e(slug)}"></head>'
            + f'<body><a href="/s/{e(slug)}">{e(title)}</a></body></html>')
    return HTMLResponse(page)


@router.post("/storefronts/{slug}/rfq")
async def rfq(slug: str, body: RfqIn, request: Request):
    doc = await _published(slug)
    if body.website_hp:
        return Response(status_code=204)  # bot: pretend success, store nothing
    co = await _company(doc)
    (_demo_limiter if co.get("is_demo_company") else _limiter).check(
        f"{request.client.host if request.client else '-'}|{slug}")
    db, now = get_db(), datetime.now(timezone.utc)
    cid = doc["company_id"]
    lead = {
        "company_id": cid, "source": "rfq", "company_name": body.company_name, "country": body.country,
        "contact_name": body.contact_name, "email": body.email, "website": None, "notes": body.message,
        "status": "new", "is_demo": False, "is_hot": True, "products_of_interest": body.products,
        "quantity": body.quantity, "source_note": f"RFQ /s/{slug}", "created_at": now}
    s = await score_for_company(db, co, lead)
    lead_id = (await db.leads.insert_one({**lead, "score": s["total"], "score_breakdown": s["breakdown"]})).inserted_id
    await db.notifications.insert_one({
        "company_id": cid, "type": "rfq", "params": {"company": body.company_name}, "lead_id": str(lead_id),
        "message_tr": f"Yeni teklif talebi: {body.company_name}", "read": False, "created_at": now})
    return Response(status_code=201)
