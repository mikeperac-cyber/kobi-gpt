import io
import json

import pytest
from bson import ObjectId
from PIL import Image

from app.services import storage_service as ss
from app.services.llm_service import LLMProviderError

GOOD = {"name_tr": "Kavrulmuş Antep Fıstığı", "description_tr": "Kabuklu, kavrulmuş fıstık.",
        "material_or_ingredients": "Antep fıstığı", "unit": "kg"}
EMPTY = {"name_tr": None, "description_tr": None, "material_or_ingredients": None, "unit": None}


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "green").save(out, "JPEG")
    return out.getvalue()


@pytest.fixture(autouse=True)
def _root(tmp_path):
    ss.set_root(tmp_path)
    yield tmp_path
    ss.set_root(None)


async def _photos(db, p, root, n=1) -> list[str]:
    """The onboarding photo plus n-1 more, all owned by the producer and present on disk."""
    urls = ["/uploads/products/a.webp"] + [f"/uploads/products/x{i}.webp" for i in range(1, n)]
    (root / "products").mkdir(exist_ok=True)
    for u in urls:
        (root / "products" / u.rsplit("/", 1)[1]).write_bytes(_jpeg())
        if u != "/uploads/products/a.webp":
            await db.uploads.insert_one({"url": u, "user_id": p["user"]["id"]})
    return urls


async def _draft(p, photos):
    return await p["client"].post("/api/products/draft", json={"photos": photos})


async def test_draft_from_photo(producer, fake_llm, db, _root):
    p = await producer("Ali")
    fake_llm.responses = [json.dumps(GOOD)]
    r = await _draft(p, await _photos(db, p, _root))
    assert r.status_code == 200, r.text
    assert r.json() == {"draft": GOOD, "source": "llm"}
    assert fake_llm.prompts[0].startswith("# product_draft") and "price_floor" not in fake_llm.prompts[0]
    assert await db.agent_runs.count_documents({"type": "product_draft"}) == 1


async def test_draft_bad_unit_falls_back(producer, fake_llm, db, _root):
    p = await producer("Ali")
    fake_llm.responses = lambda _: json.dumps({**GOOD, "unit": "ton"})
    r = await _draft(p, await _photos(db, p, _root))
    assert r.status_code == 200 and r.json() == {"draft": EMPTY, "source": "template"}


async def test_draft_llm_down_falls_back(producer, fake_llm, db, _root):
    p = await producer("Ali")
    fake_llm.responses = [LLMProviderError("down")] * 3
    r = await _draft(p, await _photos(db, p, _root))
    assert r.status_code == 200 and r.json()["source"] == "template"


async def test_draft_sends_at_most_three_photos(producer, fake_llm, db, _root):
    p = await producer("Ali")
    fake_llm.responses = [json.dumps(GOOD)]
    await _draft(p, await _photos(db, p, _root, n=4))
    assert len(fake_llm.images[-1]) == 3


async def test_draft_rejects_foreign_or_missing_photo(producer, fake_llm, db, _root):
    a, b = await producer("Ali"), await producer("Veli")
    await db.uploads.insert_one({"url": "/uploads/products/veli.webp", "user_id": b["user"]["id"]})
    r = await _draft(a, ["/uploads/products/veli.webp"])
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_photo"
    assert (await _draft(a, [])).status_code == 422
    r = await _draft(a, ["/uploads/products/a.webp"])  # owned, but the file is not on disk
    assert r.status_code == 422 and r.json()["detail"]["code"] == "bad_photo"


async def test_draft_demo_cache(producer, fake_llm, db, _root):
    p = await producer("Ali")
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"is_demo_company": True}})
    photos = await _photos(db, p, _root)
    fake_llm.responses = [json.dumps(GOOD)]
    assert (await _draft(p, photos)).json()["source"] == "llm"
    fake_llm.responses = [LLMProviderError("down")] * 3
    assert (await _draft(p, photos)).json() == {"draft": GOOD, "source": "cache"}


async def test_draft_demo_cache_survives_new_upload_url(producer, fake_llm, db, _root):
    """The live demo uploads a fresh photo (new uuid URL): the cache must key on the image, not the URL."""
    p = await producer("Ali")
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"is_demo_company": True}})
    photos = await _photos(db, p, _root, n=2)
    fake_llm.responses = [json.dumps(GOOD)]
    assert (await _draft(p, photos[:1])).json()["source"] == "llm"
    fake_llm.responses = [LLMProviderError("down")] * 3
    assert (await _draft(p, photos[1:])).json() == {"draft": GOOD, "source": "cache"}  # same bytes, new URL
