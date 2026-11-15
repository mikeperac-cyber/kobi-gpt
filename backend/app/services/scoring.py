import json
import re
from pathlib import Path

from app.core.text import tr_fold

LEVEL_WEIGHTS = {"zorunlu": 3, "koşullu": 2, "önerilen": 1}


def readiness_score(items: list[dict]) -> int:
    """Weighted share of applicable checklist items that are done, 0-100 (half rounds up)."""
    applicable = [i for i in items if i["applies"]]
    total = sum(LEVEL_WEIGHTS[i["level"]] for i in applicable)
    if not total:
        return 0
    done = sum(LEVEL_WEIGHTS[i["level"]] for i in applicable if i["done"])
    return int(100 * done / total + 0.5)


# ---- lead scoring (deterministic, no LLM)
SOURCE_POINTS = {"rfq": 40, "csv_import": 20, "manual": 15, "demo": 0}  # demo leads score on content only
STOPWORDS = {"und", "der", "die", "the", "and", "for", "with", "gmbh", "ltd", "ve", "ile", "icin"}
_SECTOR_KW = json.loads((Path(__file__).resolve().parents[1] / "seed" / "data" / "keywords.json")
                        .read_text(encoding="utf-8"))


def tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", tr_fold(text or "")) if len(t) >= 3 and t not in STOPWORDS}


def product_keywords(products: list[dict], sector: str | None = None) -> set[str]:
    out = set()
    for p in products:
        out |= tokens(f"{p.get('name_tr', '')} {p.get('material_or_ingredients', '')}")
    for w in _SECTOR_KW.get(sector or "", []):
        out |= tokens(w)
    return out


def lead_score(lead: dict, products: list[dict], target_country: str, sector: str | None = None) -> dict:
    """Score a lead 0-100 from four parts, returned as {total, breakdown}:

    - source: rfq 40, csv_import 20, manual 15, demo 0 (demo leads are scored on content only)
    - product_match: min(30, 10 x number of distinct folded tokens (>= 3 chars, minus stopwords) shared by the
      lead text (company_name, notes, website, products_of_interest) and the product keywords
      (name_tr + material_or_ingredients + the sector's synonyms in seed/data/keywords.json))
    - country: 15 if the lead country equals the company's target market
    - email: 15 if the lead has a non-empty email
    Stored once when the lead is written; editing a product later does not rescore.
    """
    text = " ".join([lead.get("company_name") or "", lead.get("notes") or "", lead.get("website") or "",
                     " ".join(lead.get("products_of_interest") or [])])
    b = {
        "source": SOURCE_POINTS.get(lead.get("source"), 0),
        "product_match": min(30, 10 * len(tokens(text) & product_keywords(products, sector))),
        "country": 15 if (lead.get("country") or "").upper() == target_country.upper() else 0,
        "email": 15 if (lead.get("email") or "").strip() else 0,
    }
    return {"total": sum(b.values()), "breakdown": b}


async def score_for_company(db, company: dict, lead: dict) -> dict:
    """lead_score with the company's products and target market loaded from the db."""
    cid = str(company["_id"])
    products = await db.products.find({"company_id": cid}).to_list(500)
    market = await db.markets.find_one({"company_id": cid}) or {}
    return lead_score(lead, products, market.get("country_code") or "DE", company.get("sector"))
