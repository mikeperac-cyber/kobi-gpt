from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import DuplicateKeyError

from app.core.db import get_db
from app.core.security import current_company, current_user
from app.core.serialize import owner_product, to_json
from app.models.company import CompanyIn
from app.models.product import OnboardingIn

router = APIRouter()


@router.post("/onboarding", status_code=201)
async def onboarding(body: OnboardingIn, user: dict = Depends(current_user)):
    db, owner, now = get_db(), str(user["_id"]), datetime.now(timezone.utc)
    company = {**body.company.model_dump(), "owner_id": owner, "created_at": now}
    try:  # unique owner_id index makes this race-safe
        company["_id"] = (await db.companies.insert_one(company)).inserted_id
    except DuplicateKeyError:
        raise HTTPException(409, {"code": "company_exists", "message_key": "errors.company_exists"}) from None
    cid = str(company["_id"])
    product = {**body.product.model_dump(), "company_id": cid, "hs_code_confirmed": None, "created_at": now}
    product["_id"] = (await db.products.insert_one(product)).inserted_id
    await db.markets.insert_one({"company_id": cid, "country_code": body.market.country_code,
                                 "languages": ["de", "en"], "status": "active"})
    return {"company": to_json(company), "product": owner_product(product),
            "market": {"country_code": body.market.country_code}}


@router.get("/company")
async def get_company(company: dict = Depends(current_company)):
    return to_json(company)


@router.put("/company")
async def put_company(body: CompanyIn, company: dict = Depends(current_company)):
    await get_db().companies.update_one({"_id": company["_id"]}, {"$set": body.model_dump()})
    return to_json({**company, **body.model_dump()})
