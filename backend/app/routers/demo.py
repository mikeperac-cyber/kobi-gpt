from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import require_admin
from app.services import demo_service

router = APIRouter(prefix="/demo", dependencies=[Depends(require_admin)])


@router.get("/companies")
async def companies():
    return await demo_service.list_demo_companies(get_db())


@router.post("/reset/{key}")
async def reset(key: str):
    out = await demo_service.reset_demo_company(get_db(), key) if key in demo_service.DEMO_KEYS else None
    if out is None:
        raise HTTPException(404, {"code": "not_found", "message_key": "errors.not_found"})
    return out
