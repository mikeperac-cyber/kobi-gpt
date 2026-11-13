import pytest

from app.core.config import get_settings
from app.models.admin import PingOut
from app.services.llm_service import (
    LLMInvalidOutput,
    LLMNotConfigured,
    LLMTimeout,
    generate_json,
    generate_text,
    render_prompt,
    set_provider,
)


async def test_generate_json_retries_then_succeeds(db, fake_llm):
    fake_llm.responses = ["not json", '{"ok": true, "echo": "x"}']
    out = await generate_json("admin_ping", {}, PingOut, run_type="test", company_id=None)
    assert out.ok and len(fake_llm.prompts) == 2
    assert "not json" not in fake_llm.prompts[0]
    run = await db.agent_runs.find_one({"type": "test"})
    assert run["status"] == "ok" and run["duration_ms"] >= 0
    assert run["input_summary"].startswith("admin_ping")


async def test_generate_json_strips_fences(db, fake_llm):
    fake_llm.responses = ['```json\n{"ok": true, "echo": "x"}\n```']
    assert (await generate_json("admin_ping", {}, PingOut, run_type="t", company_id=None)).echo == "x"


async def test_generate_json_gives_up_after_two_retries(db, fake_llm):
    fake_llm.responses = ["x", "y", "z"]
    with pytest.raises(LLMInvalidOutput):
        await generate_json("admin_ping", {}, PingOut, run_type="test", company_id=None)
    assert len(fake_llm.prompts) == 3
    assert (await db.agent_runs.find_one({"type": "test"}))["status"] == "error"


async def test_provider_error_is_logged_and_raised(db, fake_llm):
    fake_llm.responses = [LLMTimeout("slow")]
    with pytest.raises(LLMTimeout):
        await generate_text("admin_ping", {}, run_type="test", company_id="c1")
    run = await db.agent_runs.find_one({"type": "test"})
    assert run["status"] == "error" and run["company_id"] == "c1" and "slow" in run["error"]


async def test_output_truncated_in_log(db, fake_llm):
    fake_llm.responses = ["a" * 9000]
    await generate_text("admin_ping", {}, run_type="test", company_id=None)
    assert len((await db.agent_runs.find_one({"type": "test"}))["output"]) <= 4000


async def test_no_key_raises_typed_error(db, monkeypatch):
    set_provider(None)
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    get_settings.cache_clear()
    with pytest.raises(LLMNotConfigured):
        await generate_text("admin_ping", {}, run_type="test", company_id=None)


def test_render_prompt_rejects_price_floor():
    with pytest.raises(ValueError):
        render_prompt("admin_ping", {"product": {"name": "x", "price_floor": 5}})
    with pytest.raises(ValueError):
        render_prompt("admin_ping", {"items": [{"a": {"price_floor": 5}}]})


@pytest.mark.xfail(reason="admin_client fixture arrives in Task 3", strict=False)
async def test_admin_llm_test_endpoint(admin_client, fake_llm):
    fake_llm.responses = ['{"ok": true, "echo": "pong"}']
    r = await admin_client.post("/api/admin/llm-test")
    assert r.json() == {"ok": True, "echo": "pong"}
