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
    """Inject the shared client with a mock transport; no backoff sleeps. Returns the call counter."""
    calls = []

    def counted(req):
        calls.append(req)
        return handler(req)
    monkeypatch.setattr(svc, "_http", httpx.AsyncClient(transport=httpx.MockTransport(counted)))
    monkeypatch.setattr(svc, "_BACKOFF", (0, 0))
    return calls


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
    class Boom:
        async def insert_one(self, *a, **k):
            raise RuntimeError("mongo down")

    class StubDb:
        agent_runs = Boom()

    monkeypatch.setattr(svc, "get_db", lambda: StubDb())
    fake_llm.responses = ["fine"]
    assert await generate_text("admin_ping", {}, run_type="t", company_id=None) == "fine"
    fake_llm.responses = [LLMTimeout("slow")]
    with pytest.raises(LLMTimeout):
        await generate_text("admin_ping", {}, run_type="t", company_id=None)


@pytest.mark.parametrize("prov,ok,cut", [
    (svc.AnthropicProvider("k", "m"), {"content": [{"type": "text", "text": "a"}], "stop_reason": "end_turn"},
     {"content": [{"type": "text", "text": "{\"a\""}], "stop_reason": "max_tokens"}),
    (svc.OpenAIProvider("k", "m"), {"choices": [{"message": {"content": "a"}, "finish_reason": "stop"}]},
     {"choices": [{"message": {"content": "{\"a\""}, "finish_reason": "length"}]}),
    (svc.GeminiProvider("k", "m"), {"candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "a"}]}}]},
     {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "{\"a\""}]}}]}),
], ids=["anthropic", "openai", "gemini"])
async def test_stop_reason_logged_and_truncation_is_invalid_output(db, monkeypatch, prov, ok, cut):
    cur = {"r": ok}
    _mock(monkeypatch, lambda req: httpx.Response(200, json=cur["r"]))
    svc.set_provider(prov)
    try:
        await generate_text("admin_ping", {}, run_type="ok", company_id=None)
        assert (await db.agent_runs.find_one({"type": "ok"}))["stop_reason"] in {"end_turn", "stop", "STOP"}
        cur["r"] = cut
        with pytest.raises(LLMInvalidOutput):
            await generate_text("admin_ping", {}, run_type="cut", company_id=None)
        run = await db.agent_runs.find_one({"type": "cut"})
        assert run["status"] == "error" and run["stop_reason"] in {"max_tokens", "length", "MAX_TOKENS"}
    finally:
        svc.set_provider(None)


async def test_anthropic_max_tokens_is_16000(monkeypatch):
    seen = {}

    def h(req):
        seen.update(_json.loads(req.content))
        return httpx.Response(200, json={"content": [{"type": "text", "text": "a"}]})

    _mock(monkeypatch, h)
    await svc.AnthropicProvider("k", "m").complete("p", [], 1, True)
    assert seen["max_tokens"] == 16000


# ---- shared client + bounded retries ----
URL = "https://api.example.test/v1"


def _seq(*resps):
    it = iter(resps)

    def h(req):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r
    return h


async def test_retry_503_then_ok(monkeypatch):
    calls = _mock(monkeypatch, _seq(httpx.Response(503, text="busy"), httpx.Response(200, json={"ok": 1})))
    assert await svc._post(URL, {}, {}, 1) == {"ok": 1}
    assert len(calls) == 2


async def test_429_every_time_stops_after_three(monkeypatch):
    calls = _mock(monkeypatch, lambda req: httpx.Response(429, text="slow down"))
    with pytest.raises(LLMProviderError):
        await svc._post(URL, {}, {}, 1)
    assert len(calls) == 3


async def test_400_not_retried(monkeypatch):
    calls = _mock(monkeypatch, lambda req: httpx.Response(400, text="bad"))
    with pytest.raises(LLMProviderError):
        await svc._post(URL, {}, {}, 1)
    assert len(calls) == 1


async def test_read_timeout_not_retried(monkeypatch):
    def h(req):
        raise httpx.ReadTimeout("slow", request=req)
    calls = _mock(monkeypatch, h)
    with pytest.raises(LLMTimeout):
        await svc._post(URL, {}, {}, 1)
    assert len(calls) == 1


async def test_connect_error_retried(monkeypatch):
    req = httpx.Request("POST", URL)
    calls = _mock(monkeypatch, _seq(httpx.ConnectError("down", request=req), httpx.Response(200, json={"ok": 2})))
    assert await svc._post(URL, {}, {}, 1) == {"ok": 2}
    assert len(calls) == 2


async def test_client_is_reused(monkeypatch):
    monkeypatch.setattr(svc, "_http", None)
    a = svc._client()
    assert svc._client() is a
    await svc.aclose()
    assert svc._http is None
