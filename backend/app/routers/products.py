from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import get_db
from app.core.security import current_company, current_user, owned
from app.core.serialize import owner_product
from app.services.upload_registry import require_owned
from app.models.product import ProductIn
from app.models.product_draft import DraftIn, ProductDraftOut
from app.services import agent_steps
from app.services.llm_service import generate_json
from app.services.storage_service import get_storage

router = APIRouter(prefix="/products")


@router.get("")
async def list_products(company: dict = Depends(current_company)):
    docs = await get_db().products.find({"company_id": str(company["_id"])}).to_list(500)
    return [owner_product(d) for d in docs]


@router.post("", status_code=201)
async def create_product(body: ProductIn, company: dict = Depends(current_company)):
    await require_owned(get_db(), body.photos, company["owner_id"])
    doc = {**body.model_dump(), "company_id": str(company["_id"]), "hs_code_confirmed": None,
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = (await get_db().products.insert_one(doc)).inserted_id
    return owner_product(doc)


@router.post("/draft")
async def draft_from_photos(body: DraftIn, user: dict = Depends(current_user), company: dict = Depends(current_company)):
    """AI suggestion for a new product from its photos; an empty draft when the model fails (never an error)."""
    await require_owned(get_db(), body.photos, company["owner_id"])
    photos = body.photos[:3]  # bound cost and latency, like the storefront analysis
    images = [b for b in (get_storage().read(u) for u in photos) if b]
    if not images:
        raise HTTPException(422, {"code": "bad_photo", "message_key": "errors.bad_photo", "fields": ["photos"]})
    ui, cid = user.get("ui_language", "tr"), str(company["_id"])
    ctx = {"ui_language": ui, "company": {k: company.get(k) for k in ("name", "sector", "city")}}

    async def call(t):
        return await generate_json("product_draft", ctx, ProductDraftOut, run_type="product_draft",
                                   company_id=cid, images=images, timeout=t)

    templated = []

    def fallback():
        templated.append(1)
        return ProductDraftOut()

    draft, fb = await agent_steps.run_ai_step(None, "product_draft", company, call, fallback,
                                              agent_steps.cache_key("product_draft", ui, *photos),
                                              ProductDraftOut.model_validate)
    source = "llm" if not fb else ("template" if templated else "cache")
    return {"draft": draft.model_dump(), "source": source}


@router.get("/{pid}")
async def get_product(pid: str, company: dict = Depends(current_company)):
    return owner_product(await owned("products", pid, str(company["_id"])))


@router.put("/{pid}")
async def put_product(pid: str, body: ProductIn, company: dict = Depends(current_company)):
    doc = await owned("products", pid, str(company["_id"]))
    await require_owned(get_db(), body.photos, company["owner_id"])
    await get_db().products.update_one({"_id": doc["_id"]}, {"$set": body.model_dump()})
    return owner_product({**doc, **body.model_dump()})


@router.delete("/{pid}")
async def delete_product(pid: str, company: dict = Depends(current_company)):
    doc = await owned("products", pid, str(company["_id"]))
    await get_db().products.delete_one({"_id": doc["_id"]})
    return {"ok": True}
