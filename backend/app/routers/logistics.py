from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.core.db import get_db
from app.core.security import current_company, owned, require_admin
from app.core.serialize import to_json
from app.models.quote import RatesIn, SampleTaskIn
from app.routers.quotes import load_rates
from app.services import logistics_service as lg
from app.services import outreach_service as svc

router = APIRouter()


def _flat(r: dict) -> dict:
    return {"packaging_pct": r["packaging_pct"]["value"], "ltl_bands": r["ltl_bands"]["bands"],
            "ftl_eur_per_truck": r["ftl"]["eur_per_truck"], "ftl_truck_capacity_kg": r["ftl"]["truck_capacity_kg"],
            "courier_eur_per_kg": r["courier"]["eur_per_kg"], "courier_min_eur": r["courier"]["min_eur"]}


@router.get("/admin/logistics-rates", dependencies=[Depends(require_admin)])
async def get_rates():
    return _flat(await load_rates(get_db()))


@router.put("/admin/logistics-rates", dependencies=[Depends(require_admin)])
async def put_rates(body: RatesIn):
    db = get_db()
    sets = {"packaging_pct": {"value": body.packaging_pct},
            "ltl_bands": {"bands": [b.model_dump() for b in body.ltl_bands]},
            "ftl": {"eur_per_truck": body.ftl_eur_per_truck, "truck_capacity_kg": body.ftl_truck_capacity_kg},
            "courier": {"eur_per_kg": body.courier_eur_per_kg, "min_eur": body.courier_min_eur}}
    for key, v in sets.items():
        await db.logistics_rates.update_one({"key": key}, {"$set": v}, upsert=True)
    return _flat(await load_rates(db))


@router.post("/leads/{lead_id}/sample-task", status_code=201)
async def sample_task(lead_id: str, body: SampleTaskIn, company: dict = Depends(current_company)):
    db, cid = get_db(), str(company["_id"])
    lead = await owned("leads", lead_id, cid)
    await owned("products", body.product_id, cid)
    if lead["status"] == "do_not_contact":
        raise svc.err(409, "do_not_contact")
    est = lg.estimate(body.sample_weight_kg, 1, await load_rates(db), "courier")
    doc = {"company_id": cid, "lead_id": lead_id, "product_id": body.product_id, "type": "numune_gonderimi",
           "checklist": [{"key": k, "done": False} for k in ("proforma", "labelling", "courier_booking")],
           "sample_weight_kg": body.sample_weight_kg, "courier_estimate": est.dict(),
           "created_at": datetime.now(timezone.utc)}
    doc["_id"] = (await db.tasks.insert_one(doc)).inserted_id
    return to_json(doc)


@router.get("/tasks")
async def list_tasks(company: dict = Depends(current_company)):
    return to_json(await get_db().tasks.find({"company_id": str(company["_id"])}).to_list(500))
