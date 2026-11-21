from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from app.core.clock import tr_today
from app.core.db import get_db
from app.services.upload_registry import record_upload
from app.core.security import current_company, current_user, owned
from app.core.serialize import public_product, to_json
from app.models.message import RejectIn
from app.models.quote import QuoteIn
from app.services import logistics_service as lg
from app.services import outreach_service as svc
from app.services.pdf_service import STRINGS, quote_pdf
from app.services.storage_service import get_storage

router = APIRouter(prefix="/quotes")
PUBLIC_KEYS = ("quantity", "unit", "incoterm", "unit_price", "currency", "payment_terms", "logistics_estimate",
               "freight_included", "total", "valid_until", "created_at")


async def load_rates(db) -> dict:
    rates = {r["key"]: r async for r in db.logistics_rates.find({})}
    if not {"packaging_pct", "ltl_bands", "ftl", "courier"} <= set(rates):
        raise svc.err(503, "rates_missing")
    return rates


@router.get("/suggest")
async def suggest(product_id: str, company: dict = Depends(current_company)):
    p = await owned("products", product_id, str(company["_id"]))
    return {"unit_price": round(p["price_floor"] * 1.25, 2), "currency": p.get("price_floor_currency", "EUR")}


@router.post("", status_code=201)
async def create(body: QuoteIn, company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    lead = await owned("leads", body.lead_id, cid)
    product = await owned("products", body.product_id, cid)
    if lead["status"] == "do_not_contact":
        raise svc.err(409, "do_not_contact")
    if body.quantity <= 0:
        raise svc.err(422, "invalid_quantity")
    if body.currency != product.get("price_floor_currency", "EUR"):
        raise svc.err(422, "floor_currency_mismatch")
    if body.unit_price < product["price_floor"]:
        raise svc.err(422, "below_floor")  # code only: the floor value never leaves the server
    if body.valid_until < tr_today():
        raise svc.err(422, "invalid_valid_until")
    weight = body.unit_weight_kg or product.get("unit_weight_kg")
    try:
        est = lg.estimate(weight, body.quantity, await load_rates(db))
    except lg.NeedsWeight:
        raise svc.err(422, "needs_weight")
    included = lg.freight_included(body.incoterm)
    if included and body.currency != "EUR":
        raise svc.err(422, "freight_currency_mismatch")
    total = round(body.quantity * body.unit_price + (est.freight_eur if included else 0), 2)
    doc = {"lead_id": body.lead_id, "company_id": cid, "product_id": body.product_id, "quantity": body.quantity,
           "unit": product["unit"], "incoterm": body.incoterm, "unit_price": body.unit_price,
           "currency": body.currency, "payment_terms": body.payment_terms, "logistics_estimate": est.dict(),
           "unit_weight_kg": weight,  # this quote's weight only; the product's weight changes in the product form
           "freight_included": included, "total": total, "valid_until": body.valid_until.isoformat(),
           "status": "draft", "pdf_url": None, "approved_by": None, "approved_at": None, "delivery_channel": None,
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = (await db.quotes.insert_one(doc)).inserted_id
    return to_json(doc)


@router.get("")
async def list_quotes(company: dict = Depends(current_company)):
    return to_json(await get_db().quotes.find({"company_id": str(company["_id"])}).to_list(500))


@router.get("/{quote_id}")
async def get_quote(quote_id: str, company: dict = Depends(current_company)):
    return to_json(await owned("quotes", quote_id, str(company["_id"])))


@router.post("/{quote_id}/approve")
async def approve(quote_id: str, company: dict = Depends(current_company), user: dict = Depends(current_user)):
    q = await owned("quotes", quote_id, str(company["_id"]))
    return to_json(await svc.approve_quote(get_db(), q["_id"], user))


@router.post("/{quote_id}/reject")
async def reject(quote_id: str, body: RejectIn, company: dict = Depends(current_company)):
    q = await owned("quotes", quote_id, str(company["_id"]))
    upd = {"status": "rejected", "reject_reason": body.reason.strip()}
    res = await get_db().quotes.update_one({"_id": q["_id"], "status": "draft"}, {"$set": upd})
    if not res.modified_count:
        raise svc.err(409, "not_draft")
    return to_json({**q, **upd})


@router.get("/{quote_id}/pdf")
async def pdf(quote_id: str, preview: int = 0, company: dict = Depends(current_company),
              user: dict = Depends(current_user)):
    db = get_db()
    q = await owned("quotes", quote_id, str(company["_id"]))
    lead = await owned("leads", q["lead_id"], str(company["_id"]))
    product = await db.products.find_one({"_id": ObjectId(q["product_id"])}) or {}
    lang = user.get("ui_language", "tr") if preview else svc.buyer_language(lead.get("country", ""))
    contact = company.get("contact") or {}
    cpub = {"name": company.get("name"), "city": company.get("city"),
            "contact": {k: contact.get(k) for k in ("email", "phone", "website")}}  # allow-list
    qpub = {**{k: q.get(k) for k in PUBLIC_KEYS},
            "buyer": {"company_name": lead.get("company_name"), "contact_name": lead.get("contact_name")}}
    data = quote_pdf(to_json(qpub), cpub, {"name_tr": public_product(product).get("name_tr")}, lang)
    if not preview:
        url = await get_storage().save_file(data, f"quotes/{company['_id']}", ".pdf")
        await record_upload(db, url, company["owner_id"])
        await db.quotes.update_one({"_id": q["_id"]}, {"$set": {"pdf_url": url}})
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{STRINGS["quote"][lang]["file"]}"'})
