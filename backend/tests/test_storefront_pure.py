import pytest

from app.core.serialize import public_product
from app.core.text import tr_fold
from app.models.storefront import IntakeIn
from app.services.storefront_service import (
    compute_missing,
    fallback_site_config,
    slugify_tr,
    template_for_sector,
    unique_slug,
)
from tests.helpers import assert_no_floor

COMPANY = {
    "name": "Bozkurt Gıda", "city": "Gaziantep", "sector": "gida",
    "description_tr": "Aile işletmesi, antep fıstığı işleriz.", "founded_year": 1998,
    "employee_count": 25, "certifications": ["ISO 22000"],
}
PRODUCT = {
    "_id": "p1", "name_tr": "Antep Fıstığı", "description_tr": "Kavrulmuş iç fıstık",
    "material_or_ingredients": "Fıstık", "unit": "kg", "moq": 500.0,
    "photos": ["/uploads/a.webp"], "price_floor": 7.77,
}


def _cfg(**kw):
    args = dict(positioning="b2b", ui_language="tr")
    args.update(kw)
    return fallback_site_config(COMPANY, [public_product(PRODUCT)], **args)


def test_slug_transliteration():
    assert slugify_tr("Bozkurt Antep Fıstığı") == "bozkurt-antep-fistigi"


def test_slug_turkish_capitals():
    assert slugify_tr("İzmir IĞDIR Çağ") == "izmir-igdir-cag"
    assert tr_fold("İÇ") == tr_fold("iç") == "ic"


async def test_unique_slug_suffix(db):
    await db.storefronts.insert_one({"slug": "acme"})
    assert await unique_slug(db, "acme") == "acme-2"
    await db.storefronts.insert_one({"slug": "acme-2"})
    assert await unique_slug(db, "acme") == "acme-3"
    assert await unique_slug(db, "fresh") == "fresh"


def test_fallback_marks_missing():
    cfg = _cfg()
    for path in ("export_info.lead_time", "export_info.sample_policy", "export_info.incoterms", "products.0.packaging"):
        assert path in cfg.missing
    assert cfg.de.export_info.lead_time is None and cfg.en.export_info.lead_time is None


def test_fallback_intake_fills_facts():
    cfg = _cfg(intake=IntakeIn(text="x", lead_time="3 weeks", incoterms=["FOB"]))
    assert cfg.de.export_info.lead_time == "3 weeks"
    assert "export_info.lead_time" not in cfg.missing
    assert "export_info.incoterms" not in cfg.missing
    assert "export_info.sample_policy" in cfg.missing


def test_fallback_has_no_floor():
    cfg = _cfg()
    assert_no_floor(cfg.model_dump())
    assert "7.77" not in cfg.model_dump_json()


def test_fallback_language_rules():
    cfg = _cfg()
    assert cfg.de.hero.cta == "Angebot anfordern" and cfg.en.hero.cta == "Request a quote"
    assert cfg.review_language == "tr" and "antep fıstığı işleriz" in cfg.review.about.story
    assert "fıstığı işleriz" not in cfg.de.model_dump_json() + cfg.en.model_dump_json()
    en = _cfg(ui_language="en")
    assert en.review_language == "en" and "fıstığı işleriz" not in en.review.model_dump_json()
    blob = (cfg.de.model_dump_json() + cfg.en.model_dump_json()).lower()
    assert not any(w in blob for w in ("beste", "weltbeste", "nr. 1", "best "))


def test_compute_missing_matches_fallback():
    cfg = _cfg()
    assert compute_missing(cfg) == cfg.missing


@pytest.mark.parametrize("sector,t", [("otomotiv_yan_sanayi", "industrial"), ("gida", "natural"),
                                      ("tekstil", "textile"), ("diger", "industrial")])
def test_template_by_sector(sector, t):
    assert template_for_sector(sector) == t


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, list):
        for v in o:
            yield from _strings(v)


def test_no_none_in_text_when_facts_missing():
    company = {"name": "Acme", "sector": "diger", "description_tr": ""}
    prod = {"id": "p9", "name_tr": "Vida", "moq": 100, "photos": []}
    cfg = fallback_site_config(company, [public_product(prod)], "b2b", "tr")
    for part in (cfg.de, cfg.en, cfg.review):
        for txt in _strings(part.model_dump()):
            assert "None" not in txt and "null" not in txt, txt
    assert cfg.de.products[0].moq == "100" and cfg.de.hero.subheadline is None
    assert "hero.subheadline" in cfg.missing and "about.founded_year" in cfg.missing
    assert "why_us" in cfg.missing and len(cfg.de.why_us) <= 4


def test_why_us_uses_product_facts_no_platform_claim():
    cfg = _cfg()
    assert 3 <= len(cfg.de.why_us) <= 4
    assert not any("Kontakt" in w for w in cfg.de.why_us)
    assert "why_us" not in cfg.missing


def test_moq_thousands_formatting():
    p = dict(PRODUCT, moq=1000000.0)
    cfg = fallback_site_config(COMPANY, [public_product(p)], "b2b", "tr")
    assert cfg.de.products[0].moq == "1.000.000 kg" and cfg.en.products[0].moq == "1,000,000 kg"
    p = dict(PRODUCT, moq=2.5, unit="adet")
    cfg = fallback_site_config(COMPANY, [public_product(p)], "b2b", "tr")
    assert cfg.en.products[0].moq == "2.5 pcs" and cfg.de.products[0].moq == "2,5 Stück"


def test_empty_products_and_slug_fallback():
    cfg = fallback_site_config(COMPANY, [], "b2b", "tr")
    assert ": ." not in cfg.de.seo.description and cfg.de.seo.description.endswith(".")
    assert slugify_tr("???") == "shop"
    assert slugify_tr("Straße") == "strasse" and tr_fold("Käse") == "kase"
