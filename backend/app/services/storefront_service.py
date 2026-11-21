import json
import re
from pathlib import Path

from bson import ObjectId

from app.core.text import tr_fold
from app.models.storefront import IntakeIn, LocalizedContent, ProductBlock, SiteConfig, Spec

_TEMPLATES = json.loads((Path(__file__).parent.parent / "seed/data/storefront_fallback.json").read_text("utf-8"))
_SECTOR_TEMPLATE = {"otomotiv_yan_sanayi": "industrial", "gida": "natural", "tekstil": "textile", "diger": "industrial"}


def template_for_sector(sector: str) -> str:
    return _SECTOR_TEMPLATE.get(sector, "industrial")


def slugify_tr(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tr_fold(text)).strip("-")[:60].strip("-") or "shop"


async def unique_slug(db, base: str, exclude_id: str | None = None) -> str:
    async def taken(s: str) -> bool:
        q: dict = {"slug": s}
        if exclude_id:
            q["_id"] = {"$ne": ObjectId(exclude_id)}
        return await db.storefronts.find_one(q) is not None

    slug, n = base, 2
    while await taken(slug):
        slug, n = f"{base}-{n}", n + 1
    return slug


def compute_missing(cfg: SiteConfig) -> list[str]:
    """Dotted paths of facts that are None (or no incoterms) in de/en; language prefix dropped, deduped."""
    found: list[str] = []

    def walk(v, path: str) -> None:
        if v is None:
            found.append(path)
        elif isinstance(v, dict):
            for k, x in v.items():
                walk(x, f"{path}.{k}" if path else k)
        elif isinstance(v, list):
            if path == "export_info.incoterms" and not v:
                found.append(path)
            for i, x in enumerate(v):
                if isinstance(x, dict):
                    walk(x, f"{path}.{i}")

    for lang in ("de", "en"):
        c = getattr(cfg, lang)
        walk(c.model_dump(), "")
        if len(c.why_us) < 3:
            found.append("why_us")
    return list(dict.fromkeys(found))


def _num(v: float, sep: str) -> str:
    """Thousands-separated, no trailing .0 (de/tr: 1.000.000, en: 1,000,000)."""
    txt = f"{v:,.2f}".rstrip("0").rstrip(".")
    dec = "," if sep == "." else "."
    return txt.replace(",", "#").replace(".", dec).replace("#", sep)


def _content(t: dict, company: dict, products: list[dict], intake: IntakeIn | None,
             own_text: str | None) -> LocalizedContent:
    # Never format a missing value into a sentence: skip the clause or leave the field None.
    name, city = company.get("name") or None, company.get("city") or None
    year, team = company.get("founded_year"), company.get("employee_count")
    certs = list(company.get("certifications") or [])
    story = (own_text or "").strip()
    if not story and name:
        story = t["story"].format(name=name, city=city) if city else t["story_nocity"].format(name=name)
        story += t["founded"].format(founded_year=year) if year else ""
        story += t["team"].format(employee_count=team) if team else ""
    story = story or None
    blocks, why = [], []
    for p in products:
        pid = p.get("id") or p.get("_id")
        if pid is None:
            continue
        # de/en never get the Turkish name: None lands in `missing` and the producer types the translation
        pname = (p.get("name_tr") or None) if own_text is not None else None
        specs = ([Spec(label=t["spec_material"], value=p["material_or_ingredients"])]
                 if p.get("material_or_ingredients") else [])
        moq = None
        if p.get("moq"):
            unit = t["units"].get(p.get("unit"), p.get("unit"))
            moq = " ".join(x for x in (_num(p["moq"], t["sep"]), unit) if x)
        blocks.append({
            "product_id": str(pid), "name": pname,
            "short": (t["product_short"].format(name=pname, company=name) if name else pname) if pname else None,
            # the producer's own Turkish text is only shown in the review copy, never in de/en
            "long": (p.get("description_tr") or None) if own_text is not None else None,
            "specs": [x.model_dump() for x in specs], "moq": moq, "photos": list(p.get("photos") or []),
        })
    if certs:
        why.append(t["why_cert"].format(certs=", ".join(certs)))
    if year:
        why.append(t["why_founded"].format(founded_year=year))
    if team:
        why.append(t["why_team"].format(employee_count=team))
    if city:
        why.append(t["why_city"].format(city=city))
    if blocks:
        why.append(t["why_products"].format(n=len(blocks)))
    why += [t["why_moq"].format(name=b["name"], moq=b["moq"]) for b in blocks if b["name"] and b["moq"]]
    names = ", ".join(b["name"] for b in blocks if b["name"])
    seo_desc = (f"{story} {t['products_label']}: {names}." if names else story) if story else None
    return LocalizedContent.model_validate({
        "hero": {"headline": name, "subheadline": t["subheadline"].format(city=city) if city else None,
                 "cta": t["cta"]},
        "about": {"story": story, "city": city, "founded_year": year, "team_size": team, "certifications": certs},
        "products": blocks,
        "why_us": why[:4],
        "export_info": {"incoterms": list(intake.incoterms) if intake else [],
                        "lead_time": intake.lead_time if intake else None,
                        "sample_policy": intake.sample_policy if intake else None},
        "rfq": {"title": t["rfq_title"], "intro": t["rfq_intro"]},
        "footer": {"note": t["footer"]},
        "seo": {"title": " – ".join(x for x in (name, city) if x) or None, "description": seo_desc},
    })


def fallback_site_config(company: dict, products: list[dict], positioning: str, ui_language: str,
                         intake: IntakeIn | None = None) -> SiteConfig:
    """Deterministic, facts-only config. de/en are never built from the producer's Turkish prose."""
    de = _content(_TEMPLATES["de"], company, products, intake, None)
    en = _content(_TEMPLATES["en"], company, products, intake, None)
    if ui_language == "tr":
        review = _content(_TEMPLATES["tr"], company, products, intake, company.get("description_tr") or "")
    else:
        review = en.model_copy(deep=True)
    cfg = SiteConfig(
        de=de, en=en, review=review, review_language="tr" if ui_language == "tr" else "en",
        slug_suggestion=slugify_tr(company.get("name", "")), template=template_for_sector(company.get("sector", "")),
        positioning=positioning)
    cfg.missing = compute_missing(cfg)
    return cfg


def drop_untranslated_names(cfg: SiteConfig, products: list[dict]) -> None:
    """Null de/en product names the model left in Turkish (and a short line built from them); recompute missing."""
    tr = {str(p.get("id") or p["_id"]): p.get("name_tr") or "" for p in products}
    for c in (cfg.de, cfg.en):
        for b in c.products:
            name_tr = tr_fold(tr.get(b.product_id, "")).strip()
            if name_tr and b.name and tr_fold(b.name).strip() == name_tr:
                b.name = None
                if b.short and name_tr in tr_fold(b.short):
                    b.short = None
    cfg.missing = compute_missing(cfg)


# ---- AI generation -------------------------------------------------------------------------------

from datetime import datetime, timezone  # noqa: E402

from pydantic import BaseModel, TypeAdapter, field_validator  # noqa: E402
from pymongo.errors import DuplicateKeyError  # noqa: E402

from app.core.serialize import public_product  # noqa: E402
from app.models.storefront import (  # noqa: E402
    About, ExportInfo, Footer, Hero, MarketAdaptation, ProductAnalysis, Rfq, Seo)
from app.services import agent_steps  # noqa: E402
from app.services.llm_service import LLMInvalidOutput, generate_json  # noqa: E402
from app.services.storage_service import get_storage  # noqa: E402

CTA = {"de": "Angebot anfordern", "en": "Request a quote"}
COMPANY_KEYS = ("name", "city", "sector", "description_tr", "founded_year", "employee_count", "certifications",
                "min_order_note")


class _Content(LocalizedContent):
    @field_validator("why_us", mode="before")
    @classmethod
    def _cap(cls, v):  # truncate instead of failing a whole step over a 5th bullet
        return v[:4] if isinstance(v, list) else v


class ContentOut(BaseModel):
    de: _Content
    en: _Content
    review: _Content
    slug_suggestion: str | None = None


_SECTION_TYPES = {"hero": Hero, "about": About, "products": list[ProductBlock], "why_us": list[str],
                  "export_info": ExportInfo, "rfq": Rfq, "footer": Footer, "seo": Seo}


class RegenOut(BaseModel):
    content: object


def _floor_forms(v: float) -> list[str]:
    return [x for f in {f"{v:g}", f"{v:.2f}"} for x in (f, f.replace(".", ","))]


def contains_floor(obj, floors: list[float]) -> bool:
    # shortcut: matches exact decimal forms only (9.5 / 9,5 / 9.50), not rounded or thousand-formatted variants;
    # the floor never enters a prompt, so this is defence in depth. Upgrade if models ever see prices.
    """True if any floor price appears as a standalone number in the generated text."""
    text = json.dumps(obj, ensure_ascii=False)
    return any(re.search(rf"(?<![\d.,]){re.escape(f)}(?!\d|[.,]\d)", text) for v in floors for f in _floor_forms(v))


def _ctx(company: dict, products: list[dict], ui_language: str, **extra) -> dict:
    drop = ("company_id", "created_at", "hs_code_confirmed")
    return {"company": {k: company.get(k) for k in COMPANY_KEYS},
            "products": [{k: v for k, v in public_product(p).items() if k not in drop} for p in products],
            "ui_language": ui_language, **extra}


def _photos(products: list[dict], limit: int = 3) -> list[bytes]:
    out, store = [], get_storage()
    for url in [u for p in products for u in p.get("photos") or []][:limit]:
        data = store.read(url)
        if data:
            out.append(data)
    return out


def _floors(products: list[dict]) -> list[float]:
    return [p["price_floor"] for p in products if p.get("price_floor")]


async def generate_site_config(job_id: str, company: dict, products: list[dict], intake: IntakeIn,
                               ui_language: str) -> SiteConfig:
    floors, cid = _floors(products), str(company["_id"])
    base = _ctx(company, products, ui_language, intake=intake.model_dump())
    pub = [public_product(p) for p in products]

    async def llm(name, schema, t, **extra):
        return await generate_json(name, {**base, **extra}, schema, run_type="storefront", company_id=cid,
                                   timeout=t, images=_photos(products) if name == "sf_product_analysis" else ())

    async def analysis_call(t):
        return await llm("sf_product_analysis", ProductAnalysis, t)

    disc = (",".join(str(p["_id"]) for p in products), intake.positioning)  # not the free-text intake

    def key(step):
        return agent_steps.cache_key(step, ui_language, *disc)

    analysis, _ = await agent_steps.run_ai_step(job_id, "analysis", company, analysis_call, ProductAnalysis,
                                                key("analysis"), ProductAnalysis.model_validate)

    async def adaptation_call(t):
        return await llm("sf_market_adaptation", MarketAdaptation, t, analysis=analysis.model_dump())

    adaptation, _ = await agent_steps.run_ai_step(job_id, "adaptation", company, adaptation_call, MarketAdaptation,
                                                  key("adaptation"), MarketAdaptation.model_validate)

    async def content_call(t):
        out = await llm("sf_content", ContentOut, t, analysis=analysis.model_dump(),
                        adaptation=adaptation.model_dump())
        if contains_floor(out.model_dump(), floors):
            raise LLMInvalidOutput("floor price in generated text")
        return out

    def content_fallback():
        f = fallback_site_config(company, pub, intake.positioning, ui_language, intake)
        return ContentOut.model_validate({**f.model_dump(include={"de", "en", "review", "slug_suggestion"})})

    out, _ = await agent_steps.run_ai_step(job_id, "content", company, content_call, content_fallback,
                                         key("content"), ContentOut.model_validate)
    if contains_floor(out.model_dump(), floors):  # also guards a cache hit
        out = content_fallback()
    # the theme step is deterministic: recorded as "template", never as an LLM result
    await agent_steps._set_step(job_id, "theme", status="done", source="template", elapsed_ms=0)

    photos = {str(p["_id"]): p.get("photos") or [] for p in products}
    for b in (*out.de.products, *out.en.products, *out.review.products):
        b.photos = list(photos.get(b.product_id, b.photos))
    out.de.hero.cta, out.en.hero.cta = CTA["de"], CTA["en"]
    cfg = SiteConfig(de=out.de, en=out.en, review=out.review, review_language=ui_language,
                     slug_suggestion=slugify_tr(out.slug_suggestion or company.get("name", "")),
                     template=template_for_sector(company.get("sector", "")), positioning=intake.positioning)
    drop_untranslated_names(cfg, products)
    return cfg


async def save_generated(db, company: dict, cfg: SiteConfig) -> dict:
    """One storefront per (company, DE). Regenerating keeps status and slug (a published URL must not move)."""
    now, cid = datetime.now(timezone.utc), str(company["_id"])
    data = {"site_config": cfg.model_dump(), "template": cfg.template, "updated_at": now}
    existing = await db.storefronts.find_one({"company_id": cid, "country": "DE"})
    if existing:
        await db.storefronts.update_one({"_id": existing["_id"]}, {"$set": data})
        return await db.storefronts.find_one({"_id": existing["_id"]})
    base = company.get("storefront_slug") or cfg.slug_suggestion or slugify_tr(company.get("name", ""))
    for _ in range(2):  # the unique index closes the check-then-insert race; retry once
        doc = {**data, "company_id": cid, "country": "DE", "status": "draft", "published_at": None,
               "slug": await unique_slug(db, base), "created_at": now}
        try:
            doc["_id"] = (await db.storefronts.insert_one(doc)).inserted_id
            return doc
        except DuplicateKeyError:
            continue
    raise RuntimeError("could not allocate a unique slug")


async def regenerate_section(company: dict, products: list[dict], cfg: SiteConfig, section: str, lang: str,
                             instruction: str | None, ui_language: str) -> tuple[object, bool, str]:
    """Returns (section as plain JSON, used_fallback, source); the unchanged section comes back on fallback.
    A demo-cache hit counts as a success (fallback False, source "cache")."""
    adapter = TypeAdapter(_SECTION_TYPES[section])
    current = adapter.dump_python(getattr(getattr(cfg, lang), section), mode="json")
    floors = _floors(products)

    def check(new):  # also runs on a cache hit
        if section == "products":  # ids and photos come from the DB, never from the model
            photos = {str(p["_id"]): p.get("photos") or [] for p in products}
            new = [{**b, "photos": list(photos[b["product_id"]])} for b in new if b["product_id"] in photos]
        if contains_floor(new, floors):
            raise LLMInvalidOutput("floor price in generated text")
        return new

    async def call(t):
        out = await generate_json(
            "sf_regen_section",
            _ctx(company, products, ui_language, section=section, lang=lang, current=current,
                 instruction=instruction or ""),
            RegenOut, run_type="storefront", company_id=str(company["_id"]), timeout=t)
        return check(adapter.dump_python(adapter.validate_python(out.content), mode="json"))

    key = agent_steps.cache_key(section, ui_language, ",".join(str(p["_id"]) for p in products), lang,
                                instruction or "")  # JSON-only value: no restore needed
    templated = []

    def tpl():
        templated.append(1)
        return current

    new, fb = await agent_steps.run_ai_step(None, section, company, call, tpl, key)
    source = "llm"
    if fb:
        try:
            new = check(new)
        except LLMInvalidOutput:
            new = current
            templated.append(1)
        if not templated:
            source, fb = "cache", False
        else:
            source = "template"
    if section == "hero":
        new["cta"] = CTA[lang]
    return new, fb, source
