import asyncio
import json

from app.core.serialize import public_product
from app.services.llm_service import LLMProviderError
from app.services.storefront_service import fallback_site_config
from tests.helpers import assert_no_floor

INTAKE = {"text": "Geleneksel kavrulmuş Antep fıstığı", "positioning": "b2b", "incoterms": ["FOB"]}


def _fixture(p, ui="tr", mutate=None):
    cfg = fallback_site_config(p["company"], [public_product(p["product"])], "b2b", ui).model_dump()
    cfg["de"]["hero"]["headline"] = "LLM Pistazien"
    cfg["de"]["hero"]["cta"] = "Jetzt kaufen"  # must be forced
    cfg["de"]["why_us"] = ["a", "b", "c", "d", "e", "f"]  # must be truncated to 4
    cfg["en"]["export_info"]["lead_time"] = None
    cfg["missing"] = []
    if mutate:
        mutate(cfg)
    return cfg


def _llm(p, **kw):
    def respond(prompt):
        if prompt.startswith("# sf_product_analysis"):
            return json.dumps({"attributes": ["x"], "selling_points": [], "quality_signals": [], "buyer_types": []})
        if prompt.startswith("# sf_market_adaptation"):
            return json.dumps({"key_messages_de": ["m"], "avoid": ["weltbeste"]})
        if prompt.startswith("# sf_content"):
            return json.dumps(_fixture(p, **kw))
        if prompt.startswith("# sf_regen_section"):
            return json.dumps({"content": {"headline": "Neu", "subheadline": None, "cta": "x"}})
        raise AssertionError(prompt[:40])
    return respond


async def _generate(p, intake=INTAKE):
    c = p["client"]
    r = await c.post("/api/storefronts/generate", json=intake)
    assert r.status_code == 200, r.text
    jid = r.json()["job_id"]
    for _ in range(200):
        job = (await c.get(f"/api/jobs/{jid}")).json()
        if job["status"] != "running":
            return job
        await asyncio.sleep(0.02)
    raise AssertionError("job stuck")


async def test_generate_happy_path(producer, fake_llm, db):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    job = await _generate(p)
    assert job["status"] == "done", job
    assert [s["key"] for s in job["steps"]] == ["analysis", "adaptation", "content", "theme"]
    assert [s["status"] for s in job["steps"]] == ["done"] * 4
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["status"] == "draft" and sf["country"] == "DE" and sf["slug"] == "bozkurt-gida"
    cfg = sf["site_config"]
    assert cfg["de"]["hero"]["headline"] == "LLM Pistazien"
    assert cfg["de"]["hero"]["cta"] == "Angebot anfordern" and cfg["en"]["hero"]["cta"] == "Request a quote"
    assert cfg["de"]["why_us"] == ["a", "b", "c", "d"]
    assert cfg["template"] == "natural" and cfg["review_language"] == "tr"
    assert_no_floor(sf)


async def test_generate_falls_back_when_llm_fails(producer, db):
    p = await producer("Ali")  # no provider, no key
    job = await _generate(p)
    assert job["status"] == "done"
    assert [s["status"] for s in job["steps"]] == ["fallback"] * 3 + ["done"]
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["site_config"]["de"]["hero"]["headline"] == "Bozkurt Gıda"


async def test_generation_prompts_exclude_floor(producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    await _generate(p)
    assert len(fake_llm.prompts) == 3
    for pr in fake_llm.prompts:
        assert "price_floor" not in pr and "9.5" not in pr


async def test_content_with_floor_value_uses_fallback(producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(p, mutate=lambda c: c["de"]["hero"].update(subheadline="Ab 9,5 EUR"))
    job = await _generate(p)
    assert [s["status"] for s in job["steps"]][2] == "fallback"
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["site_config"]["de"]["hero"]["subheadline"] != "Ab 9,5 EUR"


async def test_ui_language_in_prompts(producer, fake_llm):
    p = await producer("Ali")
    await p["client"].patch("/api/auth/me", json={"ui_language": "en"})
    fake_llm.responses = _llm(p, ui="en")
    await _generate(p)
    assert len(fake_llm.prompts) == 3
    assert all("ui_language: en" in pr for pr in fake_llm.prompts)
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["site_config"]["review_language"] == "en"


async def test_missing_recomputed(producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    await _generate(p)
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert "export_info.lead_time" in sf["site_config"]["missing"]


async def test_regenerate_section_passes_instruction(producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    await _generate(p)
    fake_llm.prompts.clear()
    body = {"section": "hero", "lang": "de", "instruction": "kürzer bitte"}
    r = await p["client"].post("/api/storefronts/mine/regenerate-section", json=body)
    assert r.status_code == 200, r.text
    assert "kürzer bitte" in fake_llm.prompts[0] and "ui_language: tr" in fake_llm.prompts[0]
    assert r.json()["fallback"] is False and r.json()["section"]["headline"] == "Neu"
    assert r.json()["section"]["cta"] == "Angebot anfordern"
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["site_config"]["de"]["hero"]["headline"] == "Neu"


async def test_regenerate_section_fallback_unchanged(producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    await _generate(p)
    before = (await p["client"].get("/api/storefronts/mine")).json()["site_config"]["en"]["seo"]
    fake_llm.responses = [LLMProviderError("x")] * 3
    r = await p["client"].post("/api/storefronts/mine/regenerate-section", json={"section": "seo", "lang": "en"})
    assert r.json() == {"section": before, "fallback": True, "missing": r.json()["missing"]}
    bad = await p["client"].post("/api/storefronts/mine/regenerate-section", json={"section": "nope", "lang": "en"})
    assert bad.status_code == 422


async def test_slug_conflict_409(producer, fake_llm):
    a, b = await producer("Ali"), await producer("Veli")
    fake_llm.responses = _llm(a)
    await _generate(a)
    await _generate(b)
    sfb = (await b["client"].get("/api/storefronts/mine")).json()
    assert sfb["slug"] == "bozkurt-gida-2"  # unique_slug suffix
    body = {"site_config": sfb["site_config"], "slug": "Bozkurt Gıda", "template": "industrial"}
    r = await b["client"].put("/api/storefronts/mine", json=body)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "slug_taken"
    body["slug"] = "Özel Fıstık"
    r = await b["client"].put("/api/storefronts/mine", json=body)
    assert r.status_code == 200 and r.json()["slug"] == "ozel-fistik" and r.json()["template"] == "industrial"
    assert r.json()["site_config"]["template"] == "industrial"


async def test_regenerate_keeps_published_status_and_slug(producer, fake_llm, db):
    p = await producer("Ali")
    fake_llm.responses = _llm(p)
    await _generate(p)
    await db.storefronts.update_one({}, {"$set": {"status": "published"}})
    await _generate(p)
    sf = (await p["client"].get("/api/storefronts/mine")).json()
    assert sf["status"] == "published" and sf["slug"] == "bozkurt-gida"
    assert await db.storefronts.count_documents({}) == 1


def test_contains_floor_is_number_boundary_aware():
    from app.services.storefront_service import contains_floor
    assert contains_floor({"a": "ab 9,5 EUR"}, [9.5]) and contains_floor({"a": "9.50"}, [9.5])
    assert not contains_floor({"a": "seit 2009,5 ; 19.5 ; ISO 22000"}, [9.5])
