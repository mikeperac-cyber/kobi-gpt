from fastapi import APIRouter, Depends

from app.core.security import require_admin
from app.models.admin import PingOut
from app.services.llm_service import generate_json

router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.post("/llm-test", response_model=PingOut)
async def llm_test():
    return await generate_json("admin_ping", {}, PingOut, run_type="llm_test", company_id=None)
