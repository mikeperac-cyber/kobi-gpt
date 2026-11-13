from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import current_company, owned
from app.core.serialize import owner_product
from app.models.product import ProductIn

router = APIRouter(prefix="/products")


@router.get("")
async def list_products(company: dict = Depends(current_company)):
    docs = await get_db().products.find({"company_id": str(company["_id"])}).to_list(500)
    return [owner_product(d) for d in docs]


@router.post("", status_code=201)
async def create_product(body: ProductIn, company: dict = Depends(current_company)):
    doc = {**body.model_dump(), "company_id": str(company["_id"]), "hs_code_confirmed": None,
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = (await get_db().products.insert_one(doc)).inserted_id
    return owner_product(doc)


@router.get("/{pid}")
async def get_product(pid: str, company: dict = Depends(current_company)):
    return owner_product(await owned("products", pid, str(company["_id"])))


@router.put("/{pid}")
async def put_product(pid: str, body: ProductIn, company: dict = Depends(current_company)):
    doc = await owned("products", pid, str(company["_id"]))
    await get_db().products.update_one({"_id": doc["_id"]}, {"$set": body.model_dump()})
    return owner_product({**doc, **body.model_dump()})


@router.delete("/{pid}")
async def delete_product(pid: str, company: dict = Depends(current_company)):
    doc = await owned("products", pid, str(company["_id"]))
    await get_db().products.delete_one({"_id": doc["_id"]})
    return {"ok": True}
