import json
from asyncio import sleep

import pytest

from app.services.llm_service import LLMError
from app.services.regai_service import keep_known
from tests.helpers import load_kb_json

RULES, INCS = load_kb_json("kb_rules"), load_kb_json("kb_incentives")


@pytest.fixture
async def kb(db):
    await db.kb_rules.insert_many([dict(r) for r in RULES])
    await db.kb_incentives.insert_many([dict(r) for r in INCS])
    await db.kb_hs_codes.insert_many([dict(r) for r in load_kb_json("kb_hs_codes")])


def fails(prompt):
    raise LLMError("down")


async def check(p, code="2008.19", channel="b2b", structural=False):
    c, pid = p["client"], p["product"]["id"]
    await c.post("/api/compliance/gtip", json={"product_id": pid, "processing": None})
    await sleep(0.1)
    r = await c.post("/api/compliance/gtip/confirm", json={"product_id": pid, "code": code})
    assert r.status_code == 200, r.text
    r = await c.post("/api/compliance/check", json={"product_id": pid, "channel": channel, "structural_use": structural})
    assert r.status_code == 200, r.text
    for _ in range(100):
        job = (await c.get(f"/api/jobs/{r.json()['job_id']}")).json()
        if job["status"] != "running":
            break
        await sleep(0.02)
    assert job["status"] == "done", job
    return (await c.get(f"/api/compliance/reports/latest?product_id={pid}")).json()


def ids(rep):
    return {i["rule_id"] for i in rep["checklist"]}


def selector(extra_rules=(), inc_ids=None):
    """LLM stand-in: selects every record present in the prompt; GTIP prompt gets an LLM error."""
    def f(prompt):
        if "records (id" in prompt:
            items = [{"rule_id": r["id"], "applies": True, "reason": "ok", "next_step": "do it"}
                     for r in RULES if f'"id": "{r["id"]}"' in prompt]
            return json.dumps({"items": items + list(extra_rules)})
        if "incentives (id" in prompt:
            return json.dumps({"items": [{"incentive_id": i["id"], "applies": True, "why": "w"}
                                         for i in INCS if inc_ids is None or i["id"] in inc_ids]})
        if "open items" in prompt:
            return json.dumps({"steps": []})
        raise LLMError("gtip not mocked")
    return f


def test_keep_known_drops_unknown_and_duplicates():
    got = keep_known([{"k": "R1"}, {"k": "R99"}, {"k": "R1"}, {"k": "R2"}], {"R1", "R2"}, "k")
    assert [g["k"] for g in got] == ["R1", "R2"]


@pytest.mark.parametrize("llm", ["fake", "none"])
async def test_seed_cases(producer, kb, fake_llm, db, llm):
    fake_llm.responses = selector() if llm == "fake" else fails
    p = await producer("Ali")
    rep = await check(p)
    assert {"R1", "R3", "R7", "R8"} <= ids(rep) and not {"R9", "R10"} & ids(rep)
    assert {"R9", "R10"} <= ids(await check(p, channel="b2c"))
    await db.companies.update_many({}, {"$set": {"sector": "tekstil"}})
    rep = await check(p, "6302.60")
    assert {"R1", "R2", "R4", "R5", "R6"} <= ids(rep)
    assert "I1" in {i["incentive_id"] for i in rep["incentives"]}
    await db.companies.update_many({}, {"$set": {"sector": "otomotiv_yan_sanayi"}})
    assert {"R1", "R2", "R12", "R13"} <= ids(await check(p, "7318.15"))


async def test_invented_rule_id_dropped(producer, kb, fake_llm):
    fake_llm.responses = selector(extra_rules=[
        {"rule_id": "R99", "applies": True, "reason": "x", "next_step": "y"},
        {"rule_id": "X1", "title": "Fake rule", "applies": True, "reason": "x", "next_step": "y"}])
    rep = await check(await producer("Ali"))
    assert ids(rep) <= {r["id"] for r in RULES}
    dump = json.dumps(rep, ensure_ascii=False)
    assert all(s not in dump for s in ("R99", "X1", "Fake rule"))


async def test_omitted_rule_is_kept_with_fallback(producer, kb, fake_llm):
    inner = selector()
    fake_llm.responses = lambda pr: json.dumps({"items": [{"rule_id": "R1", "applies": False, "reason": "n/a"}]}) \
        if "records (id" in pr else inner(pr)
    rep = await check(await producer("Ali"))
    by = {i["rule_id"]: i for i in rep["checklist"]}
    assert by["R1"]["applies"] is False and by["R3"]["applies"] is True
    assert by["R3"]["reason"] == next(r for r in RULES if r["id"] == "R3")["summary_tr"]


async def test_invented_incentive_dropped(producer, kb, fake_llm):
    inner = selector()
    fake_llm.responses = lambda pr: json.dumps({"items": [
        {"incentive_id": "I1", "applies": True, "why": "w"}, {"incentive_id": "I99", "applies": True, "why": "bad"}]}) \
        if "incentives (id" in pr else inner(pr)
    rep = await check(await producer("Ali"))
    assert [i["incentive_id"] for i in rep["incentives"]] == ["I1"] and "I99" not in json.dumps(rep)


async def test_every_item_has_kb_id_and_source(producer, kb, fake_llm):
    fake_llm.responses = fails
    rep = await check(await producer("Ali"))
    for i in rep["checklist"]:
        r = next(x for x in RULES if x["id"] == i["rule_id"])
        assert i["source_url"] == r["source_url"] and i["title_tr"] == r["title_tr"]
        assert "verified" in i and "last_verified" in i and i["done"] is False
    assert all(i["source_url"] for i in rep["incentives"])


async def test_tick_updates_score(producer, kb, fake_llm):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    assert rep["score"] == 0
    c = p["client"]
    r = await c.patch(f"/api/compliance/reports/{rep['id']}/items/R1", json={"done": True})
    assert r.status_code == 200 and r.json()["score"] > 0
    assert (await c.patch(f"/api/compliance/reports/{rep['id']}/items/R99", json={"done": True})).status_code == 404
    other = await producer("Veli")
    assert (await other["client"].patch(f"/api/compliance/reports/{rep['id']}/items/R1",
                                        json={"done": True})).status_code == 404
    latest = (await c.get(f"/api/compliance/reports/latest?product_id={p['product']['id']}")).json()
    assert latest["score"] == r.json()["score"]
    assert next(i for i in latest["checklist"] if i["rule_id"] == "R1")["done"] is True


async def test_no_match_for_unsupported_country(producer, kb, fake_llm, db):
    fake_llm.responses = selector()
    p = await producer("Ali")
    await db.markets.update_many({}, {"$set": {"country_code": "FR"}})
    rep = await check(p)
    assert rep["no_match"] is True and ids(rep) == {"R1"}
    assert all("records (id" not in x for x in fake_llm.prompts)


async def test_gtip_not_confirmed_409(producer, kb, fake_llm):
    p = await producer("Ali")
    r = await p["client"].post("/api/compliance/check", json={"product_id": p["product"]["id"]})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "gtip_not_confirmed"


async def test_prompts_carry_ui_language_and_no_floor(producer, kb, fake_llm):
    fake_llm.responses = selector()
    p = await producer("Ali")
    await p["client"].patch("/api/auth/me", json={"ui_language": "en"})
    await check(p)
    explain = [x for x in fake_llm.prompts if "records (id" in x or "incentives (id" in x or "open items" in x]
    assert len(explain) == 3
    for pr in explain:
        assert "ui_language: en" in pr and "price_floor" not in pr


async def test_fallback_next_steps_top3_by_weight(producer, kb, fake_llm):
    fake_llm.responses = fails
    rep = await check(await producer("Ali"))
    w = {"zorunlu": 3, "koşullu": 2, "önerilen": 1}
    want = sorted(rep["checklist"], key=lambda i: (-w[i["level"]], int(i["rule_id"][1:])))[:3]
    assert [s["rule_id"] for s in rep["next_steps"]] == [i["rule_id"] for i in want]


async def test_next_steps_endpoint_respects_ticks(producer, kb, fake_llm):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    c, first = p["client"], rep["next_steps"][0]["rule_id"]
    await c.patch(f"/api/compliance/reports/{rep['id']}/items/{first}", json={"done": True})
    fake_llm.responses = lambda pr: json.dumps(
        {"steps": [{"rule_id": first, "text": "x"}, {"rule_id": "R98", "text": "y"}]})
    r = await c.post(f"/api/compliance/reports/{rep['id']}/next-steps")
    assert r.status_code == 200
    got = [s["rule_id"] for s in r.json()["next_steps"]]
    assert first not in got and "R98" not in got and len(got) == 3


def test_grounded_text():
    from app.services.regai_service import grounded_text
    kb = ["CBAM (2026'dan itibaren)", "Aflatoksin limitleri"]
    assert grounded_text("18 ay içinde başvurun", kb) is None
    assert grounded_text("2026 öncesi hazırlanın", kb) == "2026 öncesi hazırlanın"
    assert grounded_text("Ücret 500 TL", kb) is None
    assert grounded_text("Limitleri kontrol edin", kb) == "Limitleri kontrol edin"
    assert grounded_text("x" * 400, kb).endswith("\u2026")


async def test_ungrounded_numbers_replaced_by_kb_text(producer, kb, fake_llm, db):
    def f(pr):
        if "records (id" in pr:
            return json.dumps({"items": [
                {"rule_id": "R7", "applies": True, "reason": "18 ay içinde başvurun", "next_step": "5000 TL ödeyin"},
                {"rule_id": "R12", "applies": True, "reason": "2026 sonrası zorunlu", "next_step": "hazırlanın"}]})
        return selector()(pr)
    fake_llm.responses = f
    p = await producer("Ali")
    rep = await check(p)
    by = {i["rule_id"]: i for i in rep["checklist"]}
    r7 = next(r for r in RULES if r["id"] == "R7")
    assert by["R7"]["reason"] == r7["summary_tr"] and by["R7"]["next_step"] == r7["what_to_do_tr"]
    assert by["R7"]["summary"] == r7["summary_tr"] and by["R7"]["what_to_do"] == r7["what_to_do_tr"]
    await db.companies.update_many({}, {"$set": {"sector": "otomotiv_yan_sanayi"}})
    by = {i["rule_id"]: i for i in (await check(p, "7318.15"))["checklist"]}
    assert by["R12"]["reason"] == "2026 sonrası zorunlu"


async def test_two_ticks_both_persist(producer, kb, fake_llm):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    c = p["client"]
    await c.patch(f"/api/compliance/reports/{rep['id']}/items/R1", json={"done": True})
    await c.patch(f"/api/compliance/reports/{rep['id']}/items/R3", json={"done": True})
    got = (await c.get(f"/api/compliance/reports/latest?product_id={p['product']['id']}")).json()
    assert {i["rule_id"] for i in got["checklist"] if i["done"]} == {"R1", "R3"}


async def test_zero_known_rule_ids_falls_back(producer, kb, fake_llm, db):
    inner = selector()
    fake_llm.responses = lambda pr: json.dumps({"items": [{"rule_id": "R99", "applies": False}]})         if "records (id" in pr else inner(pr)
    rep = await check(await producer("Ali"))
    assert all(i["applies"] for i in rep["checklist"])
    job = await db.jobs.find_one({"kind": "compliance"}, sort=[("created_at", -1)])
    assert next(s for s in job["steps"] if s["key"] == "rules")["status"] == "fallback"


async def test_latest_report_shows_live_kb_verification(producer, kb, fake_llm, admin_client, db):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    c = p["client"]
    await c.patch(f"/api/compliance/reports/{rep['id']}/items/R1", json={"done": True})
    before = next(i for i in rep["checklist"] if i["rule_id"] == "R1")
    assert not before["verified"]
    assert (await admin_client.post("/api/admin/kb/rules/R1/verify")).status_code == 200
    latest = (await c.get(f"/api/compliance/reports/latest?product_id={p['product']['id']}")).json()
    r1 = next(i for i in latest["checklist"] if i["rule_id"] == "R1")
    assert r1["verified"] is True and r1["last_verified"] and r1["done"] is True


async def test_next_steps_endpoint_cache_is_per_product(producer, kb, fake_llm, db):
    from bson import ObjectId

    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"is_demo_company": True}})
    first = rep["checklist"][0]["rule_id"]
    fake_llm.responses = lambda pr: json.dumps({"steps": [{"rule_id": first, "text": "x"}]})
    await p["client"].post(f"/api/compliance/reports/{rep['id']}/next-steps")
    keys = [d["key"] async for d in db.demo_cache.find({"key": {"$regex": "^next_steps"}})]
    assert keys and all(k.startswith(f"next_steps:tr:{rep['product_id']}:") for k in keys)
