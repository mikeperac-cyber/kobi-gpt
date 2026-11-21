import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile

from app.core.csvutil import MAX_IMPORT, parse_csv
from app.core.db import get_db
from app.core.security import current_company, owned
from app.core.serialize import to_json
from app.core.text import EMAIL as _EMAIL
from app.models.lead import PATCHABLE, STATUSES, ImportIn, LeadIn, StatusIn
from app.services.scoring import score_for_company

router = APIRouter(prefix="/leads")
pipeline_router = APIRouter()
IMPORT_TTL = timedelta(hours=1)


def _err(status, code):
    return HTTPException(status, {"code": code, "message_key": f"errors.{code}"})


def _note(s: str) -> str:
    s = (s or "").strip()
    if not s:
        raise _err(422, "source_note_required")
    return s


async def _make(db, company: dict, source: str, fields: dict, note: str, now) -> dict:
    lead = {**fields, "company_id": str(company["_id"]), "source": source, "source_note": note, "status": "new",
            "is_demo": False, "is_hot": False, "created_at": now}
    s = await score_for_company(db, company, lead)
    lead["score"], lead["score_breakdown"] = s["total"], s["breakdown"]
    lead["_id"] = (await db.leads.insert_one(lead)).inserted_id
    return lead


_SORTS = {"score": [("score", -1), ("created_at", -1)], "created_at": [("created_at", -1)],
          None: [("is_hot", -1), ("score", -1), ("created_at", -1)]}  # default: hot (RFQ) first, then score, newest


@router.get("")
async def list_leads(response: Response, sort: str | None = None, status: str | None = None,
                     limit: int = Query(100, ge=1, le=500), offset: int = Query(0, ge=0),
                     company: dict = Depends(current_company)):
    q = {"company_id": str(company["_id"])}
    if status:
        if status not in STATUSES:
            raise _err(422, "validation_error")
        q["status"] = status
    db = get_db()
    response.headers["X-Total-Count"] = str(await db.leads.count_documents(q))
    order = _SORTS.get(sort, _SORTS[None]) + [("_id", -1)]  # _id: stable pages on ties
    return to_json(await db.leads.find(q).sort(order).skip(offset).limit(limit).to_list(limit))


@router.post("", status_code=201)
async def add_lead(body: LeadIn, company: dict = Depends(current_company)):
    note = _note(body.source_note)
    f = {**body.model_dump(exclude={"source_note"}), "country": body.country.upper()}
    if f["email"] and not _EMAIL.match(f["email"]):
        raise _err(422, "validation_error")
    return to_json(await _make(get_db(), company, "manual", f, note, datetime.now(timezone.utc)))


@router.post("/import/preview")
async def import_preview(file: UploadFile = File(), company: dict = Depends(current_company)):
    raw = await file.read(MAX_IMPORT + 1)
    if len(raw) > MAX_IMPORT:
        raise _err(413, "file_too_large")
    headers, rows = parse_csv(raw)
    db, now = get_db(), datetime.now(timezone.utc)
    await db.lead_imports.delete_many({"created_at": {"$lt": now - IMPORT_TTL}})  # lazy expiry
    fid = (await db.lead_imports.insert_one({"company_id": str(company["_id"]), "headers": headers, "rows": rows,
                                             "created_at": now})).inserted_id
    return {"file_id": str(fid), "headers": headers, "rows": [[r.get(h, "") for h in headers] for r in rows[:5]],
            "total": len(rows)}


@router.post("/import")
async def import_leads(body: ImportIn, company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    note = _note(body.source_note)
    imp = await owned("lead_imports", body.file_id, cid)
    m = body.mapping
    imported, skipped, errors = 0, 0, []
    seen = {d["email"].lower() async for d in db.leads.find({"company_id": cid, "email": {"$ne": ""}})}
    now = datetime.now(timezone.utc)
    default_cc = ((await db.markets.find_one({"company_id": cid})) or {}).get("country_code") or "DE"

    for n, row in enumerate(imp["rows"], start=2):  # row 1 = header
        def get(k):
            col = getattr(m, k)
            return (row.get(col) or "").strip() if col else ""

        name, country, email = get("company_name"), get("country").upper() or default_cc, get("email")
        if not name:
            reason = "no_company_name"
        elif not re.fullmatch(r"[A-Z]{2}", country):
            reason = "bad_country"
        elif email and not _EMAIL.match(email):
            reason = "bad_email"
        elif email.lower() in seen:
            reason = "duplicate"
        else:
            reason = None
        if reason:
            skipped += 1
            errors.append({"row": n, "reason": reason})
            continue
        if email:
            seen.add(email.lower())
        await _make(db, company, "csv_import", {"company_name": name, "country": country,
                    "contact_name": get("contact_name"), "email": email, "website": get("website") or None,
                    "notes": get("notes")}, note, now)
        imported += 1
    await db.lead_imports.delete_one({"_id": imp["_id"]})
    return {"imported": imported, "skipped": skipped, "errors": errors}


@router.get("/{lead_id}")
async def get_lead(lead_id: str, company: dict = Depends(current_company)):
    return to_json(await owned("leads", lead_id, str(company["_id"])))


@router.patch("/{lead_id}")
async def patch_lead(lead_id: str, body: StatusIn, company: dict = Depends(current_company)):
    lead = await owned("leads", lead_id, str(company["_id"]))
    if body.status not in STATUSES or body.status not in PATCHABLE:
        raise _err(422, "validation_error")
    if lead["status"] == "do_not_contact" and body.status != "do_not_contact":
        raise _err(409, "lead_blocked")  # once opted out, stays
    await get_db().leads.update_one({"_id": lead["_id"]}, {"$set": {"status": body.status}})
    return to_json({**lead, "status": body.status})


@pipeline_router.get("/pipeline/stats")
async def pipeline_stats(company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    own = {"company_id": cid}
    return {"leads": await db.leads.count_documents(own),
            "messages_sent": await db.messages.count_documents({**own, "direction": "outbound", "status": "sent"}),
            "replies": await db.messages.count_documents({**own, "direction": "inbound"}),
            "quotes_sent": await db.quotes.count_documents({**own, "status": "sent"}),
            "won": await db.leads.count_documents({**own, "status": "won"})}
