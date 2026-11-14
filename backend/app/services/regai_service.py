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
    return f"{s[:4]}.{s[4:6]}" if s.isdigit() and len(s) in (6, 8, 10, 12) else None


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


# ---- Compliance report: KB-grounded, LLM may only explain ----------------------------------------------

from app.models.compliance import IncentiveExplainOut, NextStepsOut, RuleExplainOut  # noqa: E402
from app.services.scoring import LEVEL_WEIGHTS, readiness_score  # noqa: E402,F401


def keep_known(items: list[dict], allowed_ids: set[str], key: str) -> list[dict]:
    """Drop items whose id is not in the KB selection, and duplicates (first wins)."""
    seen: set[str] = set()
    out = []
    for i in items:
        if i.get(key) in allowed_ids and i[key] not in seen:
            seen.add(i[key])
            out.append(i)
    return out


def _s(v, cap: int = 300) -> str:
    v = str(v or "").strip()
    return v if len(v) <= cap else v[:cap - 1] + "…"


_NUM = re.compile(r"\d+(?:[.,]\d+)*")
_MONEY = re.compile(r"[€$%]|\b(?:TL|TRY|EUR|USD|euro|dolar|lira)\b", re.I)


def grounded_text(llm_text, kb_texts: list[str]) -> str | None:
    """LLM text, or None when it carries a number/amount that the KB record's own text does not contain."""
    text = _s(llm_text)
    if not text:
        return None
    kb = " ".join(kb_texts)
    for tok in _NUM.findall(text):
        if not re.search(rf"(?<!\d){re.escape(tok)}(?!\d)", kb):
            return None
    return None if _MONEY.search(text) and not _MONEY.search(kb) else text


def build_checklist(rules: list[dict], picked: dict[str, dict], ui: str) -> list[dict]:
    """Every matched KB rule appears; the LLM contributes only applies/reason/next_step."""
    out = []
    for r in rules:
        p = picked.get(r["id"], {})
        kb = [r[f"title_{ui}"], r[f"summary_{ui}"], r[f"what_to_do_{ui}"]]
        out.append({
            "rule_id": r["id"], "title_tr": r["title_tr"], "title_en": r["title_en"], "side": r["side"],
            "level": r["level"], "source_url": r["source_url"], "last_verified": r.get("last_verified"),
            "verified": r.get("verified", False),
            "applies": p.get("applies", True),
            "summary": r[f"summary_{ui}"], "what_to_do": r[f"what_to_do_{ui}"],
            "reason": grounded_text(p.get("reason"), kb) or r[f"summary_{ui}"],
            "next_step": grounded_text(p.get("next_step"), kb) or r[f"what_to_do_{ui}"],
            "done": False})
    return out


def fallback_next_steps(checklist: list[dict], ui: str, kb: dict[str, dict]) -> list[dict]:
    open_ = [i for i in checklist if i["applies"] and not i["done"] and i["rule_id"] in kb]
    open_.sort(key=lambda i: (-LEVEL_WEIGHTS[i["level"]], int(i["rule_id"][1:])))
    return [{"rule_id": i["rule_id"], "text": kb[i["rule_id"]][f"what_to_do_{ui}"]} for i in open_[:3]]


async def next_steps(checklist: list[dict], rules_by_id: dict[str, dict], company: dict, ui: str,
                     job_id: str | None) -> list[dict]:
    open_ = [i for i in checklist if i["applies"] and not i["done"] and i["rule_id"] in rules_by_id]
    allowed = {i["rule_id"] for i in open_}
    ctx = {"ui_language": ui, "open_items": [
        {"id": i["rule_id"], "title": i[f"title_{ui}"], "summary": rules_by_id[i["rule_id"]][f"summary_{ui}"],
         "level": i["level"]} for i in open_]}

    async def call(t):
        out = await generate_json("next_steps", ctx, NextStepsOut, run_type="next_steps",
                                  company_id=str(company["_id"]), timeout=t)
        steps = []
        for s in keep_known([s.model_dump() for s in out.steps], allowed, "rule_id"):
            r = rules_by_id[s["rule_id"]]
            kb = [r[f"title_{ui}"], r[f"summary_{ui}"], r[f"what_to_do_{ui}"]]
            steps.append({"rule_id": s["rule_id"], "text": grounded_text(s["text"], kb) or r[f"what_to_do_{ui}"]})
        if not steps:
            raise LLMInvalidOutput("no valid next steps")
        return steps

    if not open_:
        await agent_steps._set_step(job_id, "next_steps", status="done", source="template", elapsed_ms=0)
        return []
    value, _ = await agent_steps.run_ai_step(job_id, "next_steps", company, call,
                                             lambda: fallback_next_steps(checklist, ui, rules_by_id))
    return value


async def build_report(product: dict, company: dict, *, country: str, channel: str, structural_use: bool,
                       ui: str, job_id: str | None) -> dict:
    db, cid = get_db(), str(company["_id"])
    hs6 = normalize_hs6(product["hs_code_confirmed"])
    rules = match_rules(await db.kb_rules.find({}).to_list(500), country=country, hs6=hs6,
                        sector=company.get("sector", ""), channel=channel, structural_use=structural_use)
    rules_by_id = {r["id"]: r for r in rules}
    incs = filter_incentives(await db.kb_incentives.find({}).to_list(500), company.get("sector", ""))
    incs_by_id = {i["id"]: i for i in incs}
    no_match = not any(r["side"] == "DEST" for r in rules)
    pub = public_product(product)
    base = {"ui_language": ui,
            "company": {"sector": company.get("sector"), "city": company.get("city"),
                        "description_tr": company.get("description_tr"),
                        "certifications": company.get("certifications", [])}}

    async def explain_rules(t):
        ctx = {**base, "country": country, "channel": channel,
               "product": {k: pub.get(k) for k in ("name_tr", "description_tr", "material_or_ingredients", "unit")},
               "records": [{"id": r["id"], "title": r[f"title_{ui}"], "summary": r[f"summary_{ui}"],
                            "level": r["level"], "side": r["side"]} for r in rules]}
        out = await generate_json("rules_explain", ctx, RuleExplainOut, run_type="rules_explain",
                                  company_id=cid, timeout=t)
        kept = keep_known([i.model_dump() for i in out.items], set(rules_by_id), "rule_id")
        if not kept:
            raise LLMInvalidOutput("no valid rule items")
        return {i["rule_id"]: i for i in kept}

    if no_match:  # nothing but the Turkish-side rule: no target-market data, so nothing to explain
        await agent_steps._set_step(job_id, "rules", status="done", source="template", elapsed_ms=0)
        picked = {}
    else:
        picked, _ = await agent_steps.run_ai_step(job_id, "rules", company, explain_rules, dict)
    checklist = build_checklist(rules, picked, ui)

    async def explain_incentives(t):
        ctx = {**base, "checklist": [{"id": i["rule_id"], "title": i[f"title_{ui}"]} for i in checklist],
               "incentives": [{"id": i["id"], "name": i[f"name_{ui}"], "provider": i["provider"],
                               "summary": i[f"summary_{ui}"]} for i in incs]}
        out = await generate_json("incentives_explain", ctx, IncentiveExplainOut, run_type="incentives_explain",
                                  company_id=cid, timeout=t)
        kept = keep_known([i.model_dump() for i in out.items], set(incs_by_id), "incentive_id")
        if not kept:
            raise LLMInvalidOutput("no valid incentives")
        return [(i["incentive_id"], grounded_text(i["why"], [incs_by_id[i["incentive_id"]][f"{k}_{ui}"]
                                                             for k in ("name", "summary", "what_to_do")]))
                for i in kept if i["applies"]]

    if incs:
        chosen, _ = await agent_steps.run_ai_step(job_id, "incentives", company, explain_incentives,
                                                  lambda: [(i["id"], i[f"summary_{ui}"]) for i in incs])
    else:
        await agent_steps._set_step(job_id, "incentives", status="done", source="template", elapsed_ms=0)
        chosen = []
    incentives = [{"incentive_id": iid, "name_tr": incs_by_id[iid]["name_tr"], "name_en": incs_by_id[iid]["name_en"],
                   "provider": incs_by_id[iid]["provider"], "source_url": incs_by_id[iid]["source_url"],
                   "summary": incs_by_id[iid][f"summary_{ui}"],
                   "why": why or incs_by_id[iid][f"summary_{ui}"]} for iid, why in chosen]

    steps = await next_steps(checklist, rules_by_id, company, ui, job_id)
    classification = await get_db().classifications.find_one({"product_id": str(product["_id"])}) or {}
    return {"product_id": str(product["_id"]), "company_id": cid, "country": country, "channel": channel,
            "structural_use": structural_use, "hs6": hs6, "candidates": classification.get("candidates", []),
            "checklist": checklist, "incentives": incentives, "next_steps": steps,
            "score": readiness_score(checklist), "no_match": no_match, "ui_language": ui}
