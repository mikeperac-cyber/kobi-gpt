from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health():
    s = get_settings()
    return {"status": "ok", "llm": {"provider": s.llm_provider, "key_set": bool(s.llm_key)}}
