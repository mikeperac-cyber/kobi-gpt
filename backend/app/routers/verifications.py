"""Supplier document verification: producers submit private documents, admins check them.
Buyers only ever see the outcome (see verification_service.public_trust), never the documents."""
from datetime import datetime, timezone

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.clock import tr_today
from app.core.db import get_db
from app.core.security import current_company, current_user, owned, require_admin
from app.core.serialize import to_json
from app.models.message import RejectIn
from app.models.verification import VerificationIn
from app.services.storage_service import get_storage
from app.services.upload_registry import require_owned
from app.services.verification_service import fold

router = APIRouter(prefix="/verifications")
admin_router = APIRouter(prefix="/admin/verifications", dependencies=[Depends(require_admin)])


def _err(status: int, code: str) -> HTTPException:
    return HTTPException(status, {"code": code, "message_key": f"errors.{code}"})


@router.post("", status_code=201)
async def submit(body: VerificationIn, company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    if not body.file_url.startswith("/uploads/documents/"):
        raise _err(422, "bad_document")
    await require_owned(db, [body.file_url], company["owner_id"])
    if body.kind == "certificate":
        if fold(body.name) not in {fold(c) for c in company.get("certifications") or []}:
            raise _err(422, "unknown_certificate")
        name = body.name.strip()
    else:
        name = "tax_plate"
    if body.valid_until and body.valid_until < tr_today():
        raise _err(422, "expired_document")
    # a new submission supersedes open or rejected ones for the same document; verified ones stay until expiry
    old = await db.verifications.find({"company_id": cid, "kind": body.kind,
                                       "status": {"$in": ["pending", "rejected"]}}).to_list(100)
    stale = [d["_id"] for d in old if fold(d["name"]) == fold(name)]
    if stale:
        await db.verifications.delete_many({"_id": {"$in": stale}})
    doc = {"company_id": cid, "kind": body.kind, "name": name, "issuer": body.issuer.strip(),
           "valid_until": body.valid_until.isoformat() if body.valid_until else None, "file_url": body.file_url,
           "status": "pending", "reject_reason": None, "reviewed_by": None, "reviewed_at": None,
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = (await db.verifications.insert_one(doc)).inserted_id
    return to_json(doc)


@router.get("")
async def mine(company: dict = Depends(current_company)):
    docs = await get_db().verifications.find({"company_id": str(company["_id"])}).sort("created_at", -1).to_list(200)
    return to_json(docs)


@router.delete("/{vid}")
async def withdraw(vid: str, company: dict = Depends(current_company)):
    doc = await owned("verifications", vid, str(company["_id"]))
    if doc["status"] != "pending":
        raise _err(409, "not_pending")
    await get_db().verifications.delete_one({"_id": doc["_id"]})
    return {"ok": True}


async def _get(vid: str) -> dict:
    try:
        doc = await get_db().verifications.find_one({"_id": ObjectId(vid)})
    except (InvalidId, TypeError):
        doc = None
    if not doc:
        raise _err(404, "not_found")
    return doc


@admin_router.get("")
async def review_queue(status: str = "pending"):
    if status not in ("pending", "verified", "rejected"):
        raise _err(422, "validation_error")
    db = get_db()
    docs = await db.verifications.find({"status": status}).sort("created_at", 1).to_list(500)
    names = {str(c["_id"]): c.get("name") async for c in
             db.companies.find({"_id": {"$in": list({ObjectId(d["company_id"]) for d in docs})}}, {"name": 1})}
    return to_json([{**d, "company_name": names.get(d["company_id"])} for d in docs])


@admin_router.get("/{vid}/file")
async def document_file(vid: str):
    doc = await _get(vid)
    data = get_storage().read(doc["file_url"])
    if data is None:
        raise _err(404, "not_found")
    media = "application/pdf" if doc["file_url"].endswith(".pdf") else "image/webp"
    return Response(data, media_type=media, headers={"Content-Disposition": "inline"})


async def _decide(vid: str, admin: dict, status: str, reason: str | None) -> dict:
    doc = await _get(vid)
    patch = {"status": status, "reject_reason": reason, "reviewed_by": str(admin["_id"]),
             "reviewed_at": datetime.now(timezone.utc)}
    res = await get_db().verifications.update_one({"_id": doc["_id"], "status": "pending"}, {"$set": patch})
    if not res.modified_count:
        raise _err(409, "not_pending")
    return to_json({**doc, **patch})


@admin_router.post("/{vid}/verify")
async def verify(vid: str, admin: dict = Depends(current_user)):
    return await _decide(vid, admin, "verified", None)


@admin_router.post("/{vid}/reject")
async def reject(vid: str, body: RejectIn, admin: dict = Depends(current_user)):
    return await _decide(vid, admin, "rejected", body.reason.strip())
