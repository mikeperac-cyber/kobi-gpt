"""Single entry point for every LLM call: raw-httpx providers, JSON validation, run logging."""
import asyncio
import base64
import contextvars
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import get_settings
from app.core.db import get_db

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
log = logging.getLogger(__name__)
M = TypeVar("M", bound=BaseModel)


class LLMError(Exception): ...
class LLMNotConfigured(LLMError): ...
class LLMTimeout(LLMError): ...
class LLMInvalidOutput(LLMError):
    def __init__(self, msg: str, raw: str = ""):
        super().__init__(msg)
        self.raw = raw

class LLMProviderError(LLMError): ...


_stop_reason: contextvars.ContextVar[str | None] = contextvars.ContextVar("llm_stop_reason", default=None)
_TRUNCATED = {"max_tokens", "length", "MAX_TOKENS"}


def _finish(reason: str | None, text: str) -> str:
    """Record the provider's stop reason for agent_runs; a cut-off reply is never usable JSON."""
    _stop_reason.set(reason)
    if reason in _TRUNCATED:
        raise LLMInvalidOutput(f"output truncated ({reason})", text)
    return text


class Provider(Protocol):
    async def complete(self, prompt: str, images: list[bytes], timeout: float, json_mode: bool) -> str: ...


_http: httpx.AsyncClient | None = None
_BACKOFF = (0.5, 1.5)  # seconds before retry 1 and 2: at most 3 attempts
_RETRY_STATUS = {429, 500, 502, 503, 504}


def _client() -> httpx.AsyncClient:
    """One pooled client for every provider call; per-request timeouts."""
    global _http
    if _http is None:
        _http = httpx.AsyncClient()
    return _http


async def aclose() -> None:
    global _http
    if _http is not None:
        await _http.aclose()
        _http = None


async def _post(url: str, headers: dict, body: dict, timeout: float) -> dict:
    # Read timeouts are not retried: agent_steps owns the demo time budget and falls back on LLMTimeout.
    for attempt in range(len(_BACKOFF) + 1):
        last = attempt == len(_BACKOFF)
        try:
            r = await _client().post(url, headers=headers, json=body, timeout=timeout)
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            if last:
                raise (LLMTimeout if isinstance(e, httpx.ConnectTimeout) else LLMProviderError)(str(e) or "connect") from e
        except httpx.TimeoutException as e:
            raise LLMTimeout(str(e) or "timeout") from e
        except httpx.HTTPError as e:
            raise LLMProviderError(str(e)) from e
        else:
            if r.status_code not in _RETRY_STATUS or last:
                break
        await asyncio.sleep(_BACKOFF[attempt])
    if not 200 <= r.status_code < 300:
        raise LLMProviderError(f"{r.status_code}: {r.text[:300]}")
    try:
        return r.json()
    except ValueError as e:
        raise LLMProviderError(f"non-JSON response: {r.text[:200]}") from e


def _extract(fn, data):
    try:
        return fn(data)
    except (KeyError, IndexError, TypeError, AttributeError) as e:
        raise LLMProviderError(f"unexpected response shape: {str(data)[:300]}") from e


def _b64(img: bytes) -> str:
    return base64.b64encode(img).decode()


def _mime(img: bytes) -> str:
    return "image/png" if img[:4] == b"\x89PNG" else "image/webp" if img[8:12] == b"WEBP" else "image/jpeg"


class AnthropicProvider:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model

    async def complete(self, prompt, images, timeout, json_mode):
        content = [
            {"type": "image", "source": {"type": "base64", "media_type": _mime(i), "data": _b64(i)}}
            for i in images
        ] + [{"type": "text", "text": prompt}]
        data = await _post(
            "https://api.anthropic.com/v1/messages",
            {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
            {"model": self.model, "max_tokens": 16000, "messages": [{"role": "user", "content": content}]},
            timeout,
        )
        text = _extract(lambda d: "".join(b.get("text", "") for b in d["content"]), data)
        return _finish(data.get("stop_reason"), text)


class OpenAIProvider:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model

    async def complete(self, prompt, images, timeout, json_mode):
        content = [
            {"type": "image_url", "image_url": {"url": f"data:{_mime(i)};base64,{_b64(i)}"}} for i in images
        ] + [{"type": "text", "text": prompt}]
        body = {"model": self.model, "messages": [{"role": "user", "content": content}]}
        if json_mode:
            body["response_format"] = {"type": "json_object"}
        data = await _post(
            "https://api.openai.com/v1/chat/completions", {"Authorization": f"Bearer {self.key}"}, body, timeout
        )
        text = _extract(lambda d: d["choices"][0]["message"]["content"] or "", data)
        return _finish(data["choices"][0].get("finish_reason"), text)


class GeminiProvider:
    def __init__(self, key: str, model: str):
        self.key, self.model = key, model

    async def complete(self, prompt, images, timeout, json_mode):
        parts = [{"inline_data": {"mime_type": _mime(i), "data": _b64(i)}} for i in images] + [{"text": prompt}]
        body = {"contents": [{"parts": parts}]}
        if json_mode:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        data = await _post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
            {"x-goog-api-key": self.key},
            body,
            timeout,
        )
        text = _extract(lambda d: "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]), data)
        return _finish(data["candidates"][0].get("finishReason"), text)


_PROVIDERS = {"anthropic": AnthropicProvider, "openai": OpenAIProvider, "gemini": GeminiProvider}
_provider: Provider | None = None


def set_provider(p: Provider | None) -> None:
    global _provider
    _provider = p


def _get_provider() -> Provider:
    if _provider is not None:
        return _provider
    s = get_settings()
    cls = _PROVIDERS.get(s.llm_provider)
    if cls is None or not s.llm_key:
        raise LLMNotConfigured(f"no API key configured for provider '{s.llm_provider}'")
    return cls(s.llm_key, s.llm_model)


def _has_price_floor(v) -> bool:
    if isinstance(v, dict):
        return "price_floor" in v or any(_has_price_floor(x) for x in v.values())
    if isinstance(v, (list, tuple)):
        return any(_has_price_floor(x) for x in v)
    return False


def render_prompt(name: str, context: dict) -> str:
    if _has_price_floor(context):
        raise ValueError("price_floor in prompt context")
    values = {k: v if isinstance(v, str) else json.dumps(v, ensure_ascii=False) for k, v in context.items()}
    return Template((PROMPTS / f"{name}.md").read_text(encoding="utf-8")).substitute(values)


async def _logged(name, prompt, run_type, company_id, work):
    start = time.perf_counter()
    output, error = "", None
    _stop_reason.set(None)
    try:
        result = await work()
        output = result if isinstance(result, str) else result.model_dump_json()
        return result
    except Exception as e:
        error = f"{type(e).__name__}: {e}"
        output = getattr(e, "raw", "")
        raise
    finally:
        doc = (
            {
                "type": run_type,
                "company_id": company_id,
                "input_summary": f"{name}: {prompt[:300]}",
                "output": output[:4000],
                "status": "error" if error else "ok",
                "duration_ms": int((time.perf_counter() - start) * 1000),
                "error": error,
                "stop_reason": _stop_reason.get(),
                "created_at": datetime.now(timezone.utc),
            }
        )
        try:
            await get_db().agent_runs.insert_one(doc)
        except Exception:  # logging must never mask the real result or error
            log.exception("failed to write agent_runs")


def _timeout(timeout: float | None) -> float:
    return timeout if timeout is not None else get_settings().llm_timeout_seconds


async def generate_text(name, context, *, run_type, company_id, images=(), timeout=None) -> str:
    prompt = render_prompt(name, context)

    async def work():
        return await _get_provider().complete(prompt, list(images), _timeout(timeout), False)

    return await _logged(name, prompt, run_type, company_id, work)


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL)


async def generate_json(name, context, schema: type[M], *, run_type, company_id, images=(), timeout=None) -> M:
    prompt = render_prompt(name, context)

    async def work():
        provider, current = _get_provider(), prompt
        raw = ""
        for _ in range(3):
            raw = (await provider.complete(current, list(images), _timeout(timeout), True)).strip()
            m = _FENCE.match(raw)
            try:
                return schema.model_validate_json(m.group(1) if m else raw)
            except ValidationError as e:
                last = str(e)
            current = (
                f"{prompt}\n\nYour previous reply was not valid. Error: {last[:500]}\n"
                "Reply again with ONLY the corrected JSON."
            )
        raise LLMInvalidOutput(last, raw)

    return await _logged(name, prompt, run_type, company_id, work)
