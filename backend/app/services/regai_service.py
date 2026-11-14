"""Pure, deterministic KB matching. The LLM only ever sees what these functions return."""


def match_rules(rules: list[dict], *, country: str, hs6: str, sector: str,
                channel: str, structural_use: bool) -> list[dict]:
    def ok(r: dict) -> bool:
        return (
            (not r.get("country") or r["country"] == country)
            and (not r.get("hs_prefixes") or any(hs6.startswith(p) for p in r["hs_prefixes"]))
            and (not r.get("sectors") or sector in r["sectors"])
            and (r.get("channel") is None or r["channel"] == channel)
            and (r.get("structural_use") is None or structural_use)
        )

    return sorted((r for r in rules if ok(r)), key=lambda r: int(r["id"][1:]))


def filter_incentives(incentives: list[dict], sector: str) -> list[dict]:
    return [i for i in incentives if not i.get("sectors") or sector in i["sectors"]]


# ---- GTİP suggestion -------------------------------------------------------------------------------

import re  # noqa: E402

from app.core.db import get_db  # noqa: E402
from app.core.serialize import public_product  # noqa: E402
from app.models.compliance import GtipCandidate, GtipOut  # noqa: E402
from app.services import agent_steps  # noqa: E402
from app.services.llm_service import LLMInvalidOutput, generate_json  # noqa: E402
from app.services.storefront_service import _photos  # noqa: E402

RANK = {"roasted": ["2008.19"], "raw": ["0802.51", "0802.52"]}


def normalize_hs6(code: str) -> str | None:
    s = re.sub(r"[.\s]", "", str(code))
    return f"{s[:4]}.{s[4:6]}" if s.isdigit() and len(s) >= 6 else None


def gtip_context(kb: list[dict], ui: str) -> list[dict]:
    return [{"code": r["id"], "description": r.get(f"description_{ui}", ""), "note": r.get(f"note_{ui}", "")}
            for r in kb]


def _fallback(kb: list[dict], sector: str, processing: str | None, ui: str) -> list[GtipCandidate]:
    order = RANK.get(processing or "", [])
    rows = sorted((r for r in kb if r.get("sector") == sector),
                  key=lambda r: order.index(r["id"]) if r["id"] in order else len(order))
    return [GtipCandidate(code=r["id"], description=r.get(f"description_{ui}", ""), confidence="orta",
                          reasoning=r.get(f"description_{ui}", ""), in_kb=True) for r in rows[:3]]


async def suggest_gtip(product: dict, company: dict, processing: str | None, ui_language: str,
                       job_id: str | None) -> list[GtipCandidate]:
    kb = await get_db().kb_hs_codes.find({}).to_list(500)
    known, cid = {r["id"] for r in kb}, str(company["_id"])
    pub = public_product(product)
    ctx = {"ui_language": ui_language, "processing": processing,
           "product": {k: pub.get(k) for k in ("name_tr", "description_tr", "material_or_ingredients", "unit")},
           "company": {"sector": company.get("sector"), "description_tr": company.get("description_tr")},
           "reference": gtip_context(kb, ui_language)}

    async def call(t):
        out = await generate_json("gtip_suggest", ctx, GtipOut, run_type="gtip", company_id=cid, timeout=t,
                                  images=_photos([product]))
        seen: list[GtipCandidate] = []
        for c in out.candidates:
            code = normalize_hs6(c.code)
            if code and code not in {s.code for s in seen}:
                seen.append(GtipCandidate(**{**c.model_dump(), "code": code}, in_kb=code in known))
        if not seen:
            raise ValueError("no valid HS candidates")
        return seen[:3]

    # ValueError is not caught by run_ai_step, so convert it to the fallback path via LLMInvalidOutput
    async def guarded(t):
        try:
            return await call(t)
        except ValueError as e:
            raise LLMInvalidOutput(str(e)) from e

    value, _ = await agent_steps.run_ai_step(
        job_id, "gtip", company, guarded, lambda: _fallback(kb, company.get("sector", ""), processing, ui_language))
    return value
