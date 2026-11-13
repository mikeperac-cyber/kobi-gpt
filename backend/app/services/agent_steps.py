import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Awaitable, Callable, TypeVar

from bson import ObjectId
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.db import get_db
from app.services.llm_service import LLMError

T = TypeVar("T")
log = logging.getLogger(__name__)
_tasks: set[asyncio.Task] = set()


def _now():
    return datetime.now(timezone.utc)


async def create_job(db, company_id: str, kind: str, steps: list[str]) -> str:
    doc = {"company_id": company_id, "kind": kind, "status": "running", "result": None, "created_at": _now(),
           "steps": [{"key": k, "status": "waiting", "source": None, "elapsed_ms": None, "started_at": None}
                     for k in steps]}
    return str((await db.jobs.insert_one(doc)).inserted_id)


async def _set_step(job_id: str | None, step: str, **fields):
    if job_id:
        await get_db().jobs.update_one({"_id": ObjectId(job_id), "steps.key": step},
                                       {"$set": {f"steps.$.{k}": v for k, v in fields.items()}})


async def fail_job(job_id: str | None, error: str):
    if job_id:
        await get_db().jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "error", "error": error}})


async def run_ai_step(job_id: str | None, step: str, company: dict, call: Callable[[float], Awaitable[T]],
                      fallback: Callable[[], T], cache_key: str | None = None) -> tuple[T, bool]:
    s = get_settings()
    timeout = s.demo_llm_timeout_seconds if company.get("is_demo_company") else s.llm_timeout_seconds
    t0 = time.monotonic()
    await _set_step(job_id, step, status="running", started_at=_now())
    try:
        try:
            # wait_for bounds the TOTAL step time (generate_json may retry, each with its own timeout)
            value, used_fallback = await asyncio.wait_for(call(timeout), timeout), False
        except (LLMError, asyncio.TimeoutError, ValidationError) as e:
            log.warning("AI step %s fell back: %r", step, e)
            value, used_fallback = fallback(), True  # Phase 5 inserts the demo-cache lookup here
    except Exception as e:  # a real bug: fail the job loudly, don't hide it
        await fail_job(job_id, f"{step}: {e!r}")
        raise
    await _set_step(job_id, step, status="fallback" if used_fallback else "done",
                    source="template" if used_fallback else "llm", elapsed_ms=int((time.monotonic() - t0) * 1000))
    return value, used_fallback


async def finish_job(job_id: str, result: dict):
    await get_db().jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": "done", "result": result}})


def spawn(coro, job_id: str | None = None) -> asyncio.Task:
    async def guarded():
        try:
            return await coro
        except Exception as e:
            log.exception("spawned task failed")
            await fail_job(job_id, repr(e))

    t = asyncio.create_task(guarded())
    _tasks.add(t)
    t.add_done_callback(_tasks.discard)
    return t
