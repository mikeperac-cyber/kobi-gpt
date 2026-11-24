import json
import logging
import unicodedata

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from app.core.db import get_db
from app.routers.auth import clear_cookie
from app.core.security import current_user, verify_password
from app.core.serialize import to_json
from app.services.storage_service import get_storage

router = APIRouter(prefix="/account")
# Exported = the user's own data. Internal collections (jobs, agent_runs, demo_cache, lead_imports) are not.
EXPORT = ("products", "markets", "storefronts", "classifications", "leads", "messages", "quotes", "tasks",
          "notifications", "verifications")
# Deleted = everything company-scoped, internal collections included.
DELETE = EXPORT + ("readiness_reports", "jobs", "agent_runs", "demo_cache", "lead_imports")
WORDS = {"tr": "SİL", "en": "DELETE"}
log = logging.getLogger(__name__)


def _norm(s: str) -> str:
    """NFC + Turkish-aware upper-casing + dotless-to-plain fold, so SİL / sil / SIL / sıl all match."""
    s = unicodedata.normalize("NFC", s.strip()).replace("i", "İ").replace("ı", "I").upper()
    return s.replace("İ", "I")


def _err(status: int, code: str) -> HTTPException:
    return HTTPException(status, {"code": code, "message_key": f"errors.{code}"})


class DeleteIn(BaseModel):
    confirm: str
    password: str


async def _company(user: dict) -> dict | None:
    return await get_db().companies.find_one({"owner_id": str(user["_id"])})


@router.get("/export")
async def export(user: dict = Depends(current_user)):
    db = get_db()
    company = await _company(user)
    out: dict = {"user": {k: v for k, v in user.items() if k != "password_hash"}, "company": company}
    cid = str(company["_id"]) if company else None
    for coll in EXPORT:
        out[coll] = await db[coll].find({"company_id": cid}).to_list(None) if cid else []
    pids = [str(p["_id"]) for p in out["products"]]
    out["readiness_reports"] = await db.readiness_reports.find({"product_id": {"$in": pids}}).to_list(None)
    return Response(json.dumps(to_json(out), ensure_ascii=False, indent=2), media_type="application/json",
                    headers={"Content-Disposition": 'attachment; filename="kobi-gpt-export.json"'})


@router.delete("", status_code=204)
async def delete_account(body: DeleteIn, response: Response, user: dict = Depends(current_user)):
    db = get_db()
    if _norm(body.confirm) not in {_norm(w) for w in WORDS.values()}:
        raise _err(422, "confirm_mismatch")
    if not verify_password(body.password, user["password_hash"]):
        raise _err(401, "bad_password")
    company = await _company(user)
    if user.get("is_admin") or (company and company.get("is_demo_company")):
        raise _err(409, "cannot_delete_demo")
    uid = str(user["_id"])
    if company:
        cid = str(company["_id"])
        products = await db.products.find({"company_id": cid}).to_list(None)
        for coll in DELETE:
            await db[coll].delete_many({"company_id": cid})
        await db.readiness_reports.delete_many({"product_id": {"$in": [str(p["_id"]) for p in products]}})
        await db.companies.delete_one({"_id": company["_id"]})
    # every file recorded for this user (incl. old PDFs, replaced photos); a doc's URL string proves nothing
    mine = {r["url"] async for r in db.uploads.find({"user_id": uid})}
    await db.users.delete_one({"_id": user["_id"]})
    storage = get_storage()
    for url in mine:
        try:
            await storage.delete(url)
        except (ValueError, OSError):
            log.warning("could not delete upload %s", url, exc_info=True)
    await db.uploads.delete_many({"user_id": uid})
    clear_cookie(response)
    response.status_code = 204
    return response
