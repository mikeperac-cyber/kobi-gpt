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
    return re.sub(r"[^a-z0-9]+", "-", tr_fold(text)).strip("-")[:60].strip("-")


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
        walk(getattr(cfg, lang).model_dump(), "")
    return list(dict.fromkeys(found))


def _content(t: dict, company: dict, products: list[dict], intake: IntakeIn | None,
             own_text: str | None) -> LocalizedContent:
    name, city = company.get("name"), company.get("city")
    year, team = company.get("founded_year"), company.get("employee_count")
    certs = list(company.get("certifications") or [])
    story = (own_text or "").strip()
    if not story:
        story = t["story"].format(name=name, city=city)
        story += t["founded"].format(founded_year=year) if year else ""
        story += t["team"].format(employee_count=team) if team else ""
    blocks = []
    for p in products:
        specs = ([Spec(label=t["spec_material"], value=p["material_or_ingredients"])]
                 if p.get("material_or_ingredients") else [])
        moq = f"{p['moq']:g} {t['units'].get(p.get('unit'), p.get('unit'))}" if p.get("moq") else None
        blocks.append({
            "product_id": str(p.get("id") or p.get("_id")), "name": p.get("name_tr"),
            "short": t["product_short"].format(name=p.get("name_tr"), company=name),
            # the producer's own Turkish text is only shown in the review copy, never in de/en
            "long": (p.get("description_tr") or None) if own_text is not None else None,
            "specs": [s.model_dump() for s in specs], "moq": moq, "photos": list(p.get("photos") or []),
        })
    why = []
    if certs:
        why.append(t["why_cert"].format(certs=", ".join(certs)))
    if year:
        why.append(t["why_founded"].format(founded_year=year))
    if team:
        why.append(t["why_team"].format(employee_count=team))
    why += [t["why_city"].format(city=city), t["why_direct"]]
    names = ", ".join(p.get("name_tr", "") for p in products)
    return LocalizedContent.model_validate({
        "hero": {"headline": t["headline"].format(name=name), "subheadline": t["subheadline"].format(city=city),
                 "cta": t["cta"]},
        "about": {"story": story, "city": city, "founded_year": year, "team_size": team, "certifications": certs},
        "products": blocks,
        "why_us": why[:4],
        "export_info": {"incoterms": list(intake.incoterms) if intake else [],
                        "lead_time": intake.lead_time if intake else None,
                        "sample_policy": intake.sample_policy if intake else None},
        "rfq": {"title": t["rfq_title"], "intro": t["rfq_intro"]},
        "footer": {"note": t["footer"]},
        "seo": {"title": t["seo_title"].format(name=name, city=city),
                "description": t["seo_desc"].format(name=name, city=city, products=names)},
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
