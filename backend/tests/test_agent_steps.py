import asyncio

import pytest
from bson import ObjectId

from app.services.agent_steps import create_job, run_ai_step, spawn
from app.services.llm_service import LLMProviderError


async def _job(db, cid="c1"):
    jid = await create_job(db, cid, "t", ["a"])
    return jid, lambda: db.jobs.find_one({"_id": ObjectId(jid)})


async def test_step_done_on_success(db):
    jid, get = await _job(db)
    async def call(t): return "ok"
    v, fb = await run_ai_step(jid, "a", {}, call, lambda: "fb")
    assert (v, fb) == ("ok", False)
    s = (await get())["steps"][0]
    assert s["status"] == "done" and s["source"] == "llm" and s["elapsed_ms"] is not None


async def test_step_fallback_on_llm_error(db, fake_llm):
    from app.services.llm_service import generate_text
    fake_llm.responses = [LLMProviderError("boom")] * 3
    jid, get = await _job(db)
    async def call(t): return await generate_text("admin_ping", {}, run_type="t", company_id="c1", timeout=t)
    v, fb = await run_ai_step(jid, "a", {}, call, lambda: "fb")
    assert (v, fb) == ("fb", True)
    s = (await get())["steps"][0]
    assert s["status"] == "fallback" and s["source"] == "template"


async def test_step_fallback_on_timeout(db, monkeypatch):
    monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "0.05")
    from app.core.config import get_settings
    get_settings.cache_clear()
    jid, get = await _job(db)
    async def call(t): await asyncio.sleep(1)
    v, fb = await run_ai_step(jid, "a", {}, call, lambda: "fb")
    assert fb and v == "fb"


async def test_demo_company_uses_demo_timeout(db, monkeypatch):
    monkeypatch.setenv("DEMO_LLM_TIMEOUT_SECONDS", "7")
    from app.core.config import get_settings
    get_settings.cache_clear()
    seen = []
    async def call(t): seen.append(t); return 1
    await run_ai_step(None, "a", {"is_demo_company": True}, call, lambda: 0)
    await run_ai_step(None, "a", {}, call, lambda: 0)
    assert seen == [7, 45]


async def test_unexpected_error_marks_job_error_and_raises(db):
    jid, get = await _job(db)
    async def call(t): raise KeyError("bug")
    with pytest.raises(KeyError):
        await run_ai_step(jid, "a", {}, call, lambda: 0)
    assert (await get())["status"] == "error"


async def test_spawn_marks_job_error(db):
    jid, get = await _job(db)
    async def boom(): raise RuntimeError("x")
    t = spawn(boom(), job_id=jid)
    await asyncio.gather(t, return_exceptions=True)
    await asyncio.sleep(0)
    j = await get()
    assert j["status"] == "error" and "x" in j["error"]


async def test_job_not_visible_to_other_company(producer):
    a, b = await producer("Ali"), await producer("Veli")
    from app.core.db import get_db
    jid = await create_job(get_db(), a["company"]["id"], "t", ["a"])
    r = await a["client"].get(f"/api/jobs/{jid}")
    assert r.status_code == 200 and r.json()["steps"][0]["status"] == "waiting"
    assert (await b["client"].get(f"/api/jobs/{jid}")).status_code == 404
