import csv
import io
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import ValidationError

from app.core.db import get_db
from app.core.security import require_admin
from app.models.kb import KINDS

router = APIRouter(prefix="/admin/kb", dependencies=[Depends(require_admin)])

MAX_IMPORT = 2 * 1024 * 1024
DANGER = ("=", "+", "-", "@", "\t", "\r")  # Excel treats these leading chars as formulas


def _guard(c):
    c = "" if c is None else str(c)
    return "'" + c if c.startswith(DANGER) else c


def _unguard(c: str) -> str:
    return c[1:] if c.startswith("'") and c[1:].startswith(DANGER) else c


RESET = {"verified": False, "last_verified": None, "verified_by": None}


def _kind(kind: str):
    if kind not in KINDS:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    name, model = KINDS[kind]
    return get_db()[name], model


def _list_fields(model) -> set[str]:
    return {n for n, f in model.model_fields.items() if str(f.annotation).startswith("list")}


def _validate(model, data) -> dict:
    try:
        return model.model_validate(data).model_dump()
    except ValidationError as e:
        fields = [".".join(str(p) for p in err["loc"]) for err in e.errors()]
        raise HTTPException(422, {"code": "validation_error", "message_key": "errors.validation_error",
                                  "fields": fields})


def _public(d: dict) -> dict:
    d = {k: v for k, v in d.items() if k != "_id"}
    lv = d.get("last_verified")
    if lv is not None and lv.tzinfo is None:  # mongo returns naive UTC
        d["last_verified"] = lv.replace(tzinfo=timezone.utc)
    if lv is not None:
        d["last_verified"] = d["last_verified"].isoformat()
    d.setdefault("verified", False)
    d.setdefault("last_verified", None)
    return d


async def _upsert(coll, rec: dict) -> bool:
    """Write rec; returns True if inserted. Changed content resets verification."""
    old = await coll.find_one({"id": rec["id"]})
    if old is None:
        await coll.insert_one({**rec, **RESET})
        return True
    changed = any(old.get(k) != v for k, v in rec.items())
    await coll.update_one({"id": rec["id"]}, {"$set": {**rec, **(RESET if changed else {})}})
    return False


@router.get("/{kind}")
async def list_kb(kind: str, q: str = ""):
    coll, _ = _kind(kind)
    docs = [_public(d) async for d in coll.find({})]
    docs.sort(key=lambda d: [(0, int(x)) if x.isdigit() else (1, x) for x in re.split(r"(\d+)", d["id"]) if x])  # R2 before R10
    q = q.strip().casefold()
    if q:  # shortcut: substring over the JSON-ish text of the record; fine for a few hundred records
        docs = [d for d in docs if q in str(d).casefold()]
    return docs


@router.post("/{kind}", status_code=201)
async def create_kb(kind: str, body: dict):
    coll, model = _kind(kind)
    rec = _validate(model, body)
    if await coll.find_one({"id": rec["id"]}):
        raise HTTPException(409, {"code": "kb_id_exists", "message_key": "errors.kb_id_exists"})
    await _upsert(coll, rec)
    return _public(await coll.find_one({"id": rec["id"]}))


@router.get("/{kind}/export.csv")
async def export_csv(kind: str):
    coll, model = _kind(kind)
    lists, cols = _list_fields(model), list(model.model_fields)
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols)
    async for d in coll.find({}).sort("id", 1):
        w.writerow([_guard(";".join(d.get(c) or []) if c in lists else d.get(c)) for c in cols])
    return Response("\ufeff" + out.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="kb_{kind}.csv"'})


@router.post("/{kind}/import")
async def import_csv(kind: str, request: Request):
    coll, model = _kind(kind)
    too_big = HTTPException(413, {"code": "file_too_large", "message_key": "errors.file_too_large"})
    if int(request.headers.get("content-length") or 0) > MAX_IMPORT:
        raise too_big
    raw = b""
    async for chunk in request.stream():
        raw += chunk
        if len(raw) > MAX_IMPORT:
            raise too_big
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1254", errors="replace")
    header = text.split("\n", 1)[0]
    delim = ";" if header.count(";") > header.count(",") else ","
    lists = _list_fields(model)
    recs, errors = [], []
    for n, row in enumerate(csv.DictReader(io.StringIO(text), delimiter=delim), start=2):  # row 1 = header
        data = {k.strip(): _unguard((v or "").strip()) for k, v in row.items() if k}
        for k in list(data):
            if k in lists:
                data[k] = [x.strip() for x in data[k].split(";") if x.strip()]
            elif data[k] == "" and k in model.model_fields and not model.model_fields[k].is_required():
                data[k] = model.model_fields[k].default
        try:
            recs.append(_validate(model, data))
        except HTTPException as e:
            errors.append({"row": n, "fields": e.detail["fields"]})
    if not recs and not errors:
        errors.append({"row": 1, "fields": []})
    if errors:
        raise HTTPException(422, {"code": "import_invalid", "message_key": "errors.import_invalid", "rows": errors})
    created = sum([await _upsert(coll, r) for r in recs])
    return {"imported": len(recs), "created": created}


@router.put("/{kind}/{rid}")
async def update_kb(kind: str, rid: str, body: dict):
    coll, model = _kind(kind)
    if not await coll.find_one({"id": rid}):
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    await _upsert(coll, _validate(model, {**body, "id": rid}))
    return _public(await coll.find_one({"id": rid}))


@router.post("/{kind}/{rid}/verify")
async def verify_kb(kind: str, rid: str, admin: dict = Depends(require_admin)):
    coll, _ = _kind(kind)
    res = await coll.update_one({"id": rid}, {"$set": {"verified": True, "verified_by": str(admin["_id"]),
                                                       "last_verified": datetime.now(timezone.utc)}})
    if not res.matched_count:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return _public(await coll.find_one({"id": rid}))
