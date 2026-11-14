import json
from pathlib import Path

import pytest

from app.services.llm_service import LLMError
from app.services.regai_service import normalize_hs6

HS = json.loads((Path(__file__).resolve().parents[1] / "app" / "seed" / "data" / "kb_hs_codes.json")
                .read_text(encoding="utf-8"))


@pytest.fixture
async def kb(db):
    await db.kb_hs_codes.insert_many([dict(r) for r in HS])


@pytest.mark.parametrize("raw,want", [("200819", "2008.19"), ("2008.19.00", "2008.19"), ("2008 19", "2008.19"),
                                      ("20A8", None), ("2008", None), ("", None)])
def test_hs_code_normalization(raw, want):
    assert normalize_hs6(raw) == want


async def _run(p, processing, ui="tr"):
    c = p["client"]
    r = await c.post("/api/compliance/gtip", json={"product_id": p["product"]["id"], "processing": processing})
    assert r.status_code == 200, r.text
    from asyncio import sleep
    for _ in range(50):
        job = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
        if job["status"] != "running":
            return job
        await sleep(0.02)
    raise AssertionError("job did not finish")


def cand(code, conf="yüksek"):
    return {"code": code, "description": "d", "confidence": conf, "reasoning": "r"}


async def test_suggest_marks_in_kb_and_drops_invalid(producer, kb, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [json.dumps({"candidates": [cand("200819"), cand("2008.19.00"), cand("20A8"),
                                                     cand("9999 99", "orta")]})]
    job = await _run(p, "roasted")
    assert job["status"] == "done"
    got = job["result"]["candidates"]
    assert [(c["code"], c["in_kb"]) for c in got] == [("2008.19", True), ("9999.99", False)]
    stored = (await p["client"].get(f"/api/compliance/gtip?product_id={p['product']['id']}")).json()
    assert stored["candidates"] == got and stored["confirmed_code"] is None
    assert "not roasted" in fake_llm.prompts[0] or "kavrulmamış" in fake_llm.prompts[0]


async def test_fallback_roasted_ranks_200819_first(producer, kb, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [LLMError("boom")]
    job = await _run(p, "roasted")
    got = job["result"]["candidates"]
    assert got[0]["code"] == "2008.19" and {c["confidence"] for c in got} == {"orta"}
    assert all(c["code"][:2] in ("08", "20") for c in got)  # gida only
    fake_llm.responses = [LLMError("boom")]
    assert (await _run(p, "raw"))["result"]["candidates"][0]["code"] == "0802.51"


async def test_all_invalid_llm_codes_use_fallback(producer, kb, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [json.dumps({"candidates": [cand("20A8")]})]
    got = (await _run(p, "roasted"))["result"]["candidates"]
    assert got and got[0]["code"] == "2008.19"


async def test_no_kb_codes_gives_empty(producer, db, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [LLMError("boom")]
    assert (await _run(p, None))["result"]["candidates"] == []


async def test_confirm_requires_known_code(producer, kb, fake_llm, db):
    p = await producer("Ali")
    fake_llm.responses = [json.dumps({"candidates": [cand("9999.99", "düşük")]})]
    await _run(p, "na")
    c, pid = p["client"], p["product"]["id"]
    r = await c.post("/api/compliance/gtip/confirm", json={"product_id": pid, "code": "8888.88"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "unknown_hs_code"
    assert (await c.post("/api/compliance/gtip/confirm", json={"product_id": pid, "code": "2008 19"})).status_code == 200
    assert (await c.get(f"/api/compliance/gtip?product_id={pid}")).json()["confirmed_code"] == "2008.19"
    assert (await c.get(f"/api/products/{pid}")).json()["hs_code_confirmed"] == "2008.19"


async def test_gtip_ownership(producer, kb, fake_llm):
    a, b = await producer("Ali"), await producer("Veli")
    r = await b["client"].post("/api/compliance/gtip", json={"product_id": a["product"]["id"], "processing": None})
    assert r.status_code == 404


async def test_gtip_prompt_has_ui_language(producer, kb, fake_llm):
    p = await producer("Ali")
    await p["client"].patch("/api/auth/me", json={"ui_language": "en"})
    fake_llm.responses = [json.dumps({"candidates": [cand("2008.19")]})]
    await _run(p, "roasted")
    assert "ui_language: en" in fake_llm.prompts[0]
    assert HS[2]["description_en"] in fake_llm.prompts[0] and HS[2]["description_tr"] not in fake_llm.prompts[0]
    assert "price_floor" not in fake_llm.prompts[0]
