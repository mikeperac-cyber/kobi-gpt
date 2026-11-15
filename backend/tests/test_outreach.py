import json

import pytest

from app.services.llm_service import LLMError

from app.services.outreach_service import OPTOUT, buyer_language, enforce_outreach_rules
from tests.helpers import assert_no_floor  # noqa: F401

GOOD = {"subject": "Pistazien aus Gaziantep", "body": "Guten Tag, wir sind Bozkurt Gida. Gerne senden wir Muster."}


async def _lead(db, p, **over):
    doc = {"company_id": p["company"]["id"], "source": "manual", "company_name": "Nuss GmbH", "country": "DE",
           "contact_name": "K W", "email": "k@nuss.de", "notes": "", "status": "new", "is_demo": False,
           "is_hot": False, "score": 10, "source_note": "x"}
    doc.update(over)
    return str((await db.leads.insert_one(doc)).inserted_id)


def _llm(draft=GOOD, tr="Merhaba"):
    return lambda prompt: json.dumps(draft if "outreach_first_contact" in prompt else {"text": tr})


async def test_draft_german_for_de_with_translation(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm()
    lid = await _lead(db, p)
    r = await p["client"].post(f"/api/leads/{lid}/draft", json={"tone": ["samples"]})
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["language"] == "de" and m["kind"] == "cold" and m["status"] == "draft"
    assert m["body_tr"] == "Merhaba" and m["translation_language"] == "tr" and not m["fallback"]
    assert OPTOUT["de"] in m["body"]
    assert (await db.leads.find_one({"company_id": p["company"]["id"]}))["status"] == "draft_ready"


async def test_translation_failure_is_honest(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = lambda pr: json.dumps(GOOD) if "outreach_first_contact" in pr else "not json"
    lid = await _lead(db, p)
    m = (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()
    assert m["body_tr"] is None and m["translation_fallback"] is True and m["fallback"] is False


async def test_rfq_draft_uses_rfq_message(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm()
    lid = await _lead(db, p, source="rfq", notes="Wir suchen 2 Tonnen Pistazien", is_hot=True)
    m = (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()
    assert m["kind"] == "rfq_answer"
    assert "Wir suchen 2 Tonnen Pistazien" in fake_llm.prompts[0]


async def test_draft_rejects_prices_and_floor(db, producer, fake_llm):
    p = await producer("Ali")
    lid = await _lead(db, p)
    for body in ("Der Preis ist 12,50 € pro kg.", "Preis EUR 1.000 fix", "nur $5", "ab 20 TL", "Wir bieten 9,5 an."):
        fake_llm.responses = _llm({"subject": "Hi", "body": body}, "tr")
        m = (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()
        assert m["fallback"] is True and body not in m["body"]
        assert "€" not in m["body"] and "9,5" not in m["body"] and OPTOUT["de"] in m["body"]
    fake_llm.responses = _llm({"subject": "Nur 3 EUR", "body": "Guten Tag."})
    assert (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()["fallback"] is True


async def test_llm_failure_uses_template_without_invented_facts(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [LLMError("x")] * 6
    lid = await _lead(db, p)
    m = (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()
    assert m["fallback"] is True and "Bozkurt Gıda" in m["body"] and "Antep fıstığı" in m["body"]
    assert "Mindestbestellmenge: 500 kg" in m["body"] and "IATF 16949" in m["body"] and "/s/" not in m["body"]
    assert "Lieferzeit" not in m["body"] and m["body_tr"] is None


def test_draft_word_limit_and_optout():
    body = " ".join(f"Satz {i} ist hier." for i in range(100))
    out = enforce_outreach_rules(body, [], "en")
    assert len(out.split()) <= 150 and out.endswith(OPTOUT["en"]) and "ist hier." in out
    assert enforce_outreach_rules(out, [], "en") == out  # idempotent, opt-out not duplicated
    assert enforce_outreach_rules("Hello there.", [], "de").endswith(OPTOUT["de"])
    assert enforce_outreach_rules("Price: €5", [], "en") is None
    assert enforce_outreach_rules("Our min is 9.5 units", [9.5], "en") is None


def test_buyer_language():
    assert [buyer_language(c) for c in ("DE", "at", "CH", "FR")] == ["de", "de", "de", "en"]


async def test_storefront_link_only_if_published(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = [LLMError("x")] * 12
    lid = await _lead(db, p)
    assert "/s/" not in (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()["body"]
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "slug": "bz", "status": "published"})
    assert "/s/bz" in (await p["client"].post(f"/api/leads/{lid}/draft", json={})).json()["body"]


async def test_do_not_contact_blocks_draft(db, producer, fake_llm):
    p = await producer("Ali")
    lid = await _lead(db, p, status="do_not_contact")
    r = await p["client"].post(f"/api/leads/{lid}/draft", json={})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "do_not_contact" and not fake_llm.prompts


async def test_prompts_exclude_floor(db, producer, fake_llm):
    p = await producer("Ali")  # onboarding floor is 9.5
    fake_llm.responses = _llm()
    lid = await _lead(db, p, source="rfq", notes="hi")
    await p["client"].post(f"/api/leads/{lid}/draft", json={"tone": ["formal"]})
    assert fake_llm.prompts
    for pr in fake_llm.prompts:
        assert "price_floor" not in pr and "9.5" not in pr and "9,5" not in pr


async def test_edit_rechecks_and_retranslates(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(tr="eski")
    c = p["client"]
    mid = (await c.post(f"/api/leads/{await _lead(db, p)}/draft", json={})).json()["id"]
    fake_llm.responses = _llm(tr="yeni")
    r = await c.put(f"/api/messages/{mid}", json={"subject": "S", "body": "Neuer Text."})
    assert r.status_code == 200 and r.json()["body_tr"] == "yeni" and OPTOUT["de"] in r.json()["body"]
    r = await c.put(f"/api/messages/{mid}", json={"subject": "S", "body": "Nur 5 €"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "price_in_message"
    assert (await c.put(f"/api/messages/{mid}", json={"subject": "S", "body": "x", "status": "sent"})).status_code == 422
    assert (await db.messages.find_one({}))["status"] == "draft"


@pytest.mark.parametrize("text", ["5 Euro", "1.000 Euro pro Tonne", "12 Euro pro kg", "10 dollars", "20% Rabatt",
                                  "%20 indirim", "Preis 12,50", "Euro 5", "price: 8", "fiyat 12", "7 cents"])
def test_currency_words_and_discounts_rejected(text):
    assert enforce_outreach_rules(f"Guten Tag. {text}.", [], "de") is None


@pytest.mark.parametrize("text", ["500 kg MOQ", "ISO 22000", "1998 gegründet", "100% Baumwolle", "%100 pamuk",
                                  "OEKO-TEX Standard 100"])
def test_facts_not_mistaken_for_prices(text):
    assert enforce_outreach_rules(f"Guten Tag. {text}.", [], "de") is not None


async def test_translation_with_amount_is_dropped(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm(tr="Fiyat 5 Euro")
    m = (await p["client"].post(f"/api/leads/{await _lead(db, p)}/draft", json={})).json()
    assert m["body_tr"] is None and m["translation_fallback"] is True
