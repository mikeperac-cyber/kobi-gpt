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
    assert "previous reply was not valid" in fake_llm.prompts[1] and "Error:" in fake_llm.prompts[1]
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
    run = await db.agent_runs.find_one({"type": "test"})
    assert run["status"] == "error" and run["output"] == "z"


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


# ---- provider HTTP mapping (httpx.MockTransport, no network) ----
import json as _json

import httpx

from app.services import llm_service as svc
from app.services.llm_service import LLMProviderError

PNG = bytes([137]) + b"PNG" + bytes(20)


def _mock(monkeypatch, handler):
    real = httpx.AsyncClient
    monkeypatch.setattr(svc.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler), **kw))


def _providers():
    return [svc.AnthropicProvider("k", "m"), svc.OpenAIProvider("k", "m"), svc.GeminiProvider("k", "m")]


@pytest.mark.parametrize("prov", _providers(), ids=lambda p: type(p).__name__)
async def test_timeout_maps(monkeypatch, prov):
    def h(req):
        raise httpx.ReadTimeout("slow", request=req)

    _mock(monkeypatch, h)
    with pytest.raises(LLMTimeout):
        await prov.complete("p", [], 1, False)


@pytest.mark.parametrize("prov", _providers(), ids=lambda p: type(p).__name__)
@pytest.mark.parametrize(
    "resp",
    [
        httpx.Response(500, text="boom"),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json={}),
        httpx.Response(200, json={"candidates": [{"finishReason": "SAFETY", "content": {}}], "choices": [], "content": None}),
    ],
    ids=["500", "non-json", "empty-obj", "no-parts"],
)
async def test_bad_responses_map_to_provider_error(monkeypatch, prov, resp):
    _mock(monkeypatch, lambda req: resp)
    with pytest.raises(LLMProviderError):
        await prov.complete("p", [], 1, False)


async def test_request_shapes(monkeypatch):
    seen = {}

    def h(req):
        seen[req.url.host] = (dict(req.headers), _json.loads(req.content))
        host = req.url.host
        if "anthropic" in host:
            return httpx.Response(200, json={"content": [{"type": "text", "text": "a"}]})
        if "openai" in host:
            return httpx.Response(200, json={"choices": [{"message": {"content": "o"}}]})
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": "g"}]}}]})

    _mock(monkeypatch, h)
    a, o, g = _providers()
    assert [await a.complete("p", [PNG], 1, True), await o.complete("p", [PNG], 1, True), await g.complete("p", [PNG], 1, True)] == ["a", "o", "g"]
    ah, ab = seen["api.anthropic.com"]
    assert ah["x-api-key"] == "k" and ah["anthropic-version"] == "2023-06-01"
    assert ab["messages"][0]["content"][0]["type"] == "image"
    assert ab["messages"][0]["content"][0]["source"]["media_type"] == "image/png"
    oh, ob = seen["api.openai.com"]
    assert oh["authorization"] == "Bearer k" and ob["response_format"] == {"type": "json_object"}
    assert ob["messages"][0]["content"][0]["image_url"]["url"].startswith("data:image/png;base64,")
    gh, gb = seen["generativelanguage.googleapis.com"]
    assert gh["x-goog-api-key"] == "k" and "inline_data" in gb["contents"][0]["parts"][0]
    assert gb["generationConfig"]["responseMimeType"] == "application/json"


async def test_log_failure_does_not_mask_result(db, fake_llm, monkeypatch):
    async def boom(*a, **k):
        raise RuntimeError("mongo down")

    monkeypatch.setattr(db.agent_runs, "insert_one", boom)
    fake_llm.responses = ["fine"]
    assert await generate_text("admin_ping", {}, run_type="t", company_id=None) == "fine"
    fake_llm.responses = [LLMTimeout("slow")]
    with pytest.raises(LLMTimeout):
        await generate_text("admin_ping", {}, run_type="t", company_id=None)
