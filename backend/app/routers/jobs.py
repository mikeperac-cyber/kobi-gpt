from fastapi import APIRouter, Depends

from app.core.security import current_company, owned
from app.core.serialize import to_json

router = APIRouter()


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, company: dict = Depends(current_company)):
    return to_json(await owned("jobs", job_id, str(company["_id"])))
