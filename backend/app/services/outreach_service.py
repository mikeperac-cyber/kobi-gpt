import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from bson import ObjectId
from fastapi import HTTPException

from app.core.config import get_settings
from app.core.db import get_db
from app.core.serialize import public_product
from app.models.message import DraftOut, TranslationOut
from app.services import agent_steps
from app.services.llm_service import generate_json
from app.services.storefront_service import COMPANY_KEYS, contains_floor

FALLBACK = json.loads((Path(__file__).resolve().parents[1] / "seed" / "data" / "outreach_fallback.json")
                      .read_text(encoding="utf-8"))
OPTOUT = FALLBACK["optout"]
MAX_WORDS, DAILY_LIMIT, TONES = 150, 20, {"formal", "shorter", "samples"}
_AMOUNT = re.compile(r"\d[\d.,]*\s?(?:€|\$|₺|(?:EUR|USD|TL)\b)|(?:€|\$|₺|\b(?:EUR|USD|TL))\s?\d", re.I)


class EmailProvider(Protocol):
    async def send(self, to: str, subject: str, body: str) -> str: ...


def get_email_provider() -> EmailProvider | None:
    return None  # MVP: no provider built; settings.email_provider is the hook for later


def err(status: int, code: str) -> HTTPException:
    return HTTPException(status, {"code": code, "message_key": f"errors.{code}"})


def buyer_language(country: str) -> str:
    return "de" if (country or "").upper() in {"DE", "AT", "CH"} else "en"


def has_amount(text: str) -> bool:
    return bool(_AMOUNT.search(text or ""))


def enforce_outreach_rules(body: str, floors: list[float], lang: str) -> str | None:
    """None = unusable (price or floor present) -> caller uses the template. Else <=150 words + opt-out line."""
    if has_amount(body) or contains_floor(body, floors):
        return None
    optout = OPTOUT[lang]
    has_opt = " ".join(optout.split()) in " ".join(body.split())
    limit = MAX_WORDS - (0 if has_opt else len(optout.split()))
    words = list(re.finditer(r"\S+", body))
    if len(words) > limit:
        cut = body[:words[limit - 1].end()]
        ends = [m.end() for m in re.finditer(r"[.!?](?=\s|$)", cut)]
        body = cut[:ends[-1]] if ends else cut.rstrip(" ,;:") + "."
    body = body.strip()
    return body if has_opt else f"{body}\n\n{optout}"


def fallback_draft(lead: dict, company: dict, products: list[dict], url: str | None, tone: list[str],
                   lang: str, kind: str) -> dict:
    t = FALLBACK[lang]
    names = ", ".join(p["name_tr"] for p in products[:3]) or company["name"]
    fill = {"company": company["name"], "city": company.get("city") or "", "products": names,
            "contact": lead.get("contact_name") or ""}
    parts = [(t["hello_named"] if fill["contact"] else t["hello"]).format(**fill), t[kind].format(**fill)]
    if "shorter" not in tone and company.get("certifications"):
        parts.append(t["certs"].format(certs=", ".join(company["certifications"])))
    if products and products[0].get("moq"):
        parts.append(t["moq"].format(moq=f"{products[0]['moq']:g}", unit=products[0].get("unit") or ""))
    if "samples" in tone:
        parts.append(t["samples"])
    if url:
        parts.append(t["link"].format(url=url))
    parts += [OPTOUT[lang], t["close"].format(**fill)]
    return {"subject": t[f"subject_{kind}"].format(**fill), "body": "\n\n".join(parts)}


def floors_of(products: list[dict]) -> list[float]:
    return [p["price_floor"] for p in products if p.get("price_floor")]


async def translate(text: str, ui_language: str, company: dict, lang: str) -> tuple[str | None, bool]:
    """Returns (translation, fell_back). Never fakes a translation: failure -> (None, True)."""
    if lang == ui_language:
        return text, False
    cid = str(company["_id"])

    async def call(t):
        out = await generate_json("outreach_translate", {"text": text, "target_language": ui_language,
                                  "ui_language": ui_language}, TranslationOut, run_type="outreach_translate",
                                  company_id=cid, timeout=t)
        return out.text

    return await agent_steps.run_ai_step(None, "translate", company, call, lambda: None)


async def draft_first_contact(lead: dict, company: dict, products: list[dict], storefront_url: str | None,
                              tone: list[str], ui_language: str) -> dict:
    db, cid = get_db(), str(company["_id"])
    lang = buyer_language(lead.get("country", ""))
    kind = "rfq_answer" if lead.get("source") == "rfq" else "cold"
    tone = [x for x in tone if x in TONES]
    pub = [{k: public_product(p).get(k) for k in ("name_tr", "description_tr", "material_or_ingredients", "unit",
                                                  "moq")} for p in products]
    ctx = {"ui_language": ui_language, "buyer_language": lang, "kind": kind, "tone": tone,
           "company": {k: company.get(k) for k in COMPANY_KEYS}, "products": pub,
           "storefront_url": storefront_url or "",
           "lead": {k: lead.get(k) for k in ("company_name", "country", "contact_name", "notes",
                                             "products_of_interest", "quantity")}}
    floors = floors_of(products)

    def fb():
        return fallback_draft(lead, company, products, storefront_url, tone, lang, kind)

    async def call(t):
        out = await generate_json("outreach_first_contact", ctx, DraftOut, run_type="outreach_draft",
                                  company_id=cid, timeout=t)
        body = enforce_outreach_rules(out.body, floors, lang)
        if body is None or has_amount(out.subject) or contains_floor(out.subject, floors):
            return {**fb(), "_rejected": True}
        return {"subject": out.subject.strip(), "body": body}

    draft, used_fb = await agent_steps.run_ai_step(None, "draft", company, call, fb)
    used_fb = bool(draft.pop("_rejected", False)) or used_fb
    body_tr, tr_fb = await translate(draft["body"], ui_language, company, lang)
    msg = {"lead_id": str(lead["_id"]), "company_id": cid, "direction": "outbound", "kind": kind, "language": lang,
           "subject": draft["subject"], "body": draft["body"], "body_tr": body_tr, "translation_language": ui_language,
           "translation_fallback": tr_fb, "status": "draft", "approved_by": None, "approved_at": None,
           "delivery_channel": None, "reject_reason": None, "fallback": used_fb,
           "created_at": datetime.now(timezone.utc)}
    msg["_id"] = (await db.messages.insert_one(msg)).inserted_id
    if lead.get("status") == "new":
        await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "draft_ready"}})
    return msg


async def edit_message(msg: dict, subject: str, body: str, company: dict, products: list[dict], ui_language: str):
    if msg["status"] != "draft":
        raise err(409, "not_draft")
    floors = floors_of(products)
    clean = enforce_outreach_rules(body, floors, msg["language"])
    if clean is None or has_amount(subject) or contains_floor(subject, floors):
        raise err(422, "price_in_message")
    body_tr, tr_fb = await translate(clean, ui_language, company, msg["language"])
    upd = {"subject": subject.strip(), "body": clean, "body_tr": body_tr, "translation_language": ui_language,
           "translation_fallback": tr_fb}
    await get_db().messages.update_one({"_id": msg["_id"]}, {"$set": upd})
    return {**msg, **upd}


def assert_sent_has_approval(doc: dict) -> None:
    if doc.get("status") == "sent" and not (doc.get("approved_by") and doc.get("approved_at")
                                            and doc.get("delivery_channel")):
        raise RuntimeError("message cannot be sent without approval")


async def approve_and_send(db, message_id, user: dict) -> dict:
    """The ONLY code path that sets a message to `sent`."""
    msg = await db.messages.find_one({"_id": message_id})
    if not msg or msg["status"] != "draft":
        raise err(409, "not_draft")
    lead = await db.leads.find_one({"_id": ObjectId(msg["lead_id"])})
    if lead and lead.get("status") == "do_not_contact":
        raise err(409, "do_not_contact")
    now = datetime.now(timezone.utc)
    if msg["kind"] == "cold":
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        n = await db.messages.count_documents({"company_id": msg["company_id"], "kind": "cold",
                                               "approved_at": {"$gte": midnight}})
        if n >= DAILY_LIMIT:
            raise err(429, "daily_limit")
    channel, provider = "mailto", get_email_provider()
    if get_settings().email_provider and provider:
        await provider.send((lead or {}).get("email", ""), msg["subject"], msg["body"])
        channel = get_settings().email_provider
    upd = {"status": "sent", "approved_by": str(user["_id"]), "approved_at": now, "delivery_channel": channel}
    assert_sent_has_approval({**msg, **upd})
    res = await db.messages.update_one({"_id": msg["_id"], "status": "draft"}, {"$set": upd})
    if not res.matched_count:
        raise err(409, "not_draft")
    if lead and lead.get("status") in ("new", "draft_ready"):
        await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "sent"}})
    return {**msg, **upd}
