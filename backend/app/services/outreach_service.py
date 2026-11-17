import json
import re
from datetime import datetime, timezone

from pathlib import Path
from typing import Protocol

from bson import ObjectId
from fastapi import HTTPException

from app.core.clock import tr_day_start_utc
from app.core.config import get_settings
from app.core.db import get_db
from app.core.serialize import public_product
from app.core.text import EMAIL_ANY, tr_fold
from app.models.message import DraftOut, ReplyAnalysisOut, TranslationOut
from app.services import agent_steps
from app.services.llm_service import generate_json
from app.services.storefront_service import COMPANY_KEYS, contains_floor

FALLBACK = json.loads((Path(__file__).resolve().parents[1] / "seed" / "data" / "outreach_fallback.json")
                      .read_text(encoding="utf-8"))
OPTOUT = FALLBACK["optout"]
MAX_WORDS, DAILY_LIMIT, TONES = 150, 20, {"formal", "shorter", "samples"}
_CUR = r"(?:EUR|USD|TL|euros?|dollars?|cents?|lira)"
# shortcut: digits only; word-form numbers ("zwölf Euro") slip through. Upgrade: LLM/number-word check if it matters.
_AMOUNT = re.compile(
    rf"\d[\d.,]*\s?(?:€|\$|₺|{_CUR}\b)|(?:€|\$|₺|\b{_CUR}\b)\s?\d"
    r"|(?:\d\s?%|%\s?\d+)\s?(?:Rabatt|discount|indirim)|\b(?:Rabatt|discount|indirim)\w*[^\d\n]{0,15}\d"
    r"|\b(?:Preis\w*|price\w*|fiyat\w*)[^\d\n]{0,12}\d", re.I)


RED_FLAGS = ("payment_change", "urgency", "domain_mismatch", "upfront_payment")
_FLAG_RES = {
    "payment_change": re.compile(r"\biban\b|new account|neues konto|yeni hesap|bank details (?:have )?changed"
                                 r"|bankverbindung ge(?:ae|ä)ndert", re.I),
    "urgency": re.compile(r"\bsofort\b|\burgent|\bimmediately|\bdringend|\bacil\b|within 24 hours", re.I),
    # "%100 pamuk" must not match: the 100% must sit next to a payment word
    "upfront_payment": re.compile(
        r"(?:100\s?%|%\s?100)\s*(?:advance|prepay\w*|upfront|vorkasse|vorauszahlung|peşin|ön ?ödeme)"
        r"|(?:vorkasse|peşin|advance payment|upfront)\W{0,3}(?:100\s?%|%\s?100|100\b)"
        r"|full prepayment|vollst(?:ae|ä)ndige vorauszahlung", re.I),
}
# matched on tr_fold(text): "iletişim"/"iletisim" both hit
_EXPLICIT_OPTOUT = re.compile(
    r"\b(?:kontaktieren sie (?:uns|mich) nicht mehr|nicht mehr kontaktieren|nicht mehr kontaktiert werden"
    r"|keine weiteren (?:e-?mails?|nachrichten|kontakt\w*)|bitte keine (?:e-?mails?|werbung)"
    r"|do not contact|don't contact|stop contacting|stop emailing|unsubscribe|remove (?:me|us)|take (?:me|us) off"
    r"|iletisim kurmayin|bizimle iletisime gecmeyin|bize yazmayin|listeden cikarin)\b")
_BROAD_OPTOUT = ("kein interesse", "not interested", "ilgilenmiyoruz")  # only trusted when the LLM is down


def explicit_opt_out(text: str) -> bool:
    return bool(_EXPLICIT_OPTOUT.search(tr_fold(text or "").replace("’", "'")))


def heuristic_opt_out(text: str) -> bool:
    return explicit_opt_out(text) or any(w in tr_fold(text or "") for w in _BROAD_OPTOUT)


def detect_red_flags(text: str, lead: dict) -> list[str]:
    out = [k for k in ("payment_change", "urgency", "upfront_payment") if _FLAG_RES[k].search(text or "")]
    lead_dom = (lead.get("email") or "").rpartition("@")[2].lower()
    if lead_dom and any(m.rpartition("@")[2].lower() != lead_dom for m in EMAIL_ANY.findall(text or "")):
        out.append("domain_mismatch")
    return sorted(out, key=RED_FLAGS.index)


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


def lead_ref(lead: dict) -> str:
    """Demo-cache identity of a lead: its content, not its _id (demo reset recreates the RFQ lead)."""
    return (lead.get("email") or lead.get("company_name") or str(lead["_id"])).lower()


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

    tr, fb = await agent_steps.run_ai_step(None, "translate", company, call, lambda: None,
                                           agent_steps.cache_key("translate", ui_language, lang, text))
    return (None, True) if tr and has_amount(tr) else (tr, fb)


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

    draft, used_fb = await agent_steps.run_ai_step(None, "draft", company, call, fb,
                                                agent_steps.cache_key("draft", ui_language, lead_ref(lead), kind,
                                                                      ",".join(tone)))
    if used_fb and "_rejected" not in draft and draft != fb():  # a cache hit: re-run the output checks
        body = enforce_outreach_rules(draft["body"], floors, lang)
        if body is None or has_amount(draft["subject"]) or contains_floor(draft["subject"], floors):
            draft = {**fb(), "_rejected": True}
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


async def claim_draft(coll, doc_id, now) -> None:
    """Atomic draft -> sending; the shared first step of every approval (messages and quotes)."""
    res = await coll.update_one({"_id": doc_id, "status": "draft"}, {"$set": {"status": "sending", "approved_at": now}})
    if not res.matched_count:
        raise err(409, "not_draft")


async def approve_quote(db, quote_id, user: dict) -> dict:
    """The ONLY code path that sets a quote to `sent` (same gate as messages; no daily limit)."""
    q = await db.quotes.find_one({"_id": quote_id})
    if not q or q["status"] != "draft":
        raise err(409, "not_draft")
    lead = await db.leads.find_one({"_id": ObjectId(q["lead_id"])})
    if lead and lead.get("status") == "do_not_contact":
        raise err(409, "do_not_contact")
    now = datetime.now(timezone.utc)
    await claim_draft(db.quotes, q["_id"], now)
    upd = {"status": "sent", "approved_by": str(user["_id"]), "approved_at": now, "delivery_channel": "mailto"}
    moved = False
    try:
        assert_sent_has_approval({**q, **upd})
        if lead and lead.get("status") not in ("won", "lost", "do_not_contact"):
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "quoted"}})
            moved = True
        await db.quotes.update_one({"_id": q["_id"], "status": "sending"}, {"$set": upd})  # final write: last
    except Exception:
        if moved:
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": lead["status"]}})
        await db.quotes.update_one({"_id": q["_id"], "status": "sending"},
                                   {"$set": {"status": "draft", "approved_at": None}})
        raise
    return {**q, **upd}


async def approve_and_send(db, message_id, user: dict) -> dict:
    """The ONLY code path that sets a message to `sent`."""
    msg = await db.messages.find_one({"_id": message_id})
    if not msg or msg["status"] != "draft":
        raise err(409, "not_draft")
    lead = await db.leads.find_one({"_id": ObjectId(msg["lead_id"])})
    if lead and lead.get("status") == "do_not_contact":
        raise err(409, "do_not_contact")
    now = datetime.now(timezone.utc)
    # claim first, then count (including this claim): two concurrent approves can't both pass the limit or both send
    await claim_draft(db.messages, msg["_id"], now)

    async def release():
        await db.messages.update_one({"_id": msg["_id"]}, {"$set": {"status": "draft", "approved_at": None}})

    if msg["kind"] == "cold":
        midnight = tr_day_start_utc(now)  # Turkish midnight, not UTC
        n = await db.messages.count_documents({"company_id": msg["company_id"], "kind": "cold",
                                               "status": {"$in": ["sending", "sent"]},
                                               "approved_at": {"$gte": midnight}})
        if n > DAILY_LIMIT:
            await release()
            raise err(429, "daily_limit")
    channel, provider = "mailto", get_email_provider()
    if get_settings().email_provider and provider:
        try:
            await provider.send((lead or {}).get("email", ""), msg["subject"], msg["body"])
        except Exception:
            await release()
            raise
        channel = get_settings().email_provider
    upd = {"status": "sent", "approved_by": str(user["_id"]), "approved_at": now, "delivery_channel": channel}
    moved = False
    try:
        assert_sent_has_approval({**msg, **upd})
        if lead and lead.get("status") in ("new", "draft_ready"):
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "sent"}})
            moved = True
        await db.messages.update_one({"_id": msg["_id"], "status": "sending"}, {"$set": upd})  # final write: last
    except Exception:
        if moved:
            await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": lead["status"]}})
        await release()
        raise
    return {**msg, **upd}


async def analyze_reply(lead: dict, company: dict, products: list[dict], text: str, ui_language: str) -> dict:
    """Stores the buyer's reply + analysis; creates ONE reply draft in the approval queue (never sends)."""
    db, cid = get_db(), str(company["_id"])
    lang = buyer_language(lead.get("country", ""))
    pub = [{k: public_product(p).get(k) for k in ("name_tr", "material_or_ingredients", "unit", "moq")}
           for p in products]
    ctx = {"ui_language": ui_language, "buyer_language": lang, "company": {k: company.get(k) for k in COMPANY_KEYS},
           "products": pub, "lead": {k: lead.get(k) for k in ("company_name", "country", "contact_name", "email")},
           "reply_text": text}
    floors = floors_of(products)

    async def call(t):
        return await generate_json("reply_analyze", ctx, ReplyAnalysisOut, run_type="reply_analyze",
                                   company_id=cid, timeout=t)

    out, fell_back = await agent_steps.run_ai_step(
        None, "analyze", company, call, lambda: None, agent_steps.cache_key("analyze", ui_language, lead_ref(lead), text),
        ReplyAnalysisOut.model_validate)
    heur = detect_red_flags(text, lead)
    if out:
        flags = sorted(set(heur) | (set(out.red_flags) & set(RED_FLAGS)), key=RED_FLAGS.index)
        analysis = {**out.model_dump(exclude={"suggested_reply"}), "red_flags": flags}
        optout = out.opt_out or out.intent == "not_interested"
        if explicit_opt_out(text):
            if not optout:
                analysis["opt_out_source"] = "keyword"
            analysis["opt_out"] = optout = True
    else:
        analysis = {"translation": None, "summary": [], "intent": "other", "red_flags": heur, "opt_out": False,
                    "terms": {"quantity": None, "incoterm": None, "delivery_date": None, "certifications": []}}
        optout = heuristic_opt_out(text)
        analysis["opt_out"] = optout
        if explicit_opt_out(text):
            analysis["opt_out_source"] = "keyword"
    now = datetime.now(timezone.utc)
    inbound = {"lead_id": str(lead["_id"]), "company_id": cid, "direction": "inbound", "kind": "reply",
               "language": lang, "subject": None, "body": text, "body_tr": analysis["translation"],
               "translation_language": ui_language, "translation_fallback": fell_back, "status": "received",
               "analysis": analysis, "created_at": now}
    inbound["_id"] = (await db.messages.insert_one(inbound)).inserted_id
    if optout:
        await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "do_not_contact"}})
        return {"inbound": inbound, "analysis": analysis, "draft": None}
    sug, used_fb = None, True
    if out:
        body = enforce_outreach_rules(out.suggested_reply.body, floors, lang)
        subj = out.suggested_reply.subject
        if body is not None and not has_amount(subj) and not contains_floor(subj, floors):
            sug, used_fb = {"subject": subj.strip(), "body": body}, False
    if sug is None:
        sug = fallback_draft(lead, company, [], None, ["shorter"], lang, "reply")
    body_tr, tr_fb = await translate(sug["body"], ui_language, company, lang)
    draft = {"lead_id": str(lead["_id"]), "company_id": cid, "direction": "outbound", "kind": "reply",
             "language": lang, "subject": sug["subject"], "body": sug["body"], "body_tr": body_tr,
             "translation_language": ui_language, "translation_fallback": tr_fb, "status": "draft",
             "approved_by": None, "approved_at": None, "delivery_channel": None, "reject_reason": None,
             "fallback": used_fb, "created_at": now}
    draft["_id"] = (await db.messages.insert_one(draft)).inserted_id
    if lead.get("status") in ("new", "draft_ready", "sent", "replied"):  # never move quoted/won/lost backwards
        await db.leads.update_one({"_id": lead["_id"]}, {"$set": {"status": "replied"}})
    return {"inbound": inbound, "analysis": analysis, "draft": draft}
