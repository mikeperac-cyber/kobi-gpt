import json

import pytest

from app.services.outreach_service import detect_red_flags, has_amount
from tests.helpers import assert_no_floor  # noqa: F401

GERMAN = "Guten Tag, wir interessieren uns für 2 Tonnen Pistazien, FOB Mersin, Lieferung im März. Bitte Muster senden."
ANALYSIS = {"translation": "Merhaba, 2 ton fıstık ilgimizi çekiyor.", "summary": ["a", "b", "c"],
            "intent": "asks_samples",
            "terms": {"quantity": "2 Tonnen", "incoterm": "FOB", "delivery_date": "März", "certifications": ["BRC"]},
            "red_flags": ["urgency", "made_up_flag"],
            "suggested_reply": {"subject": "Re: Pistazien", "body": "Vielen Dank, wir senden gerne Muster."},
            "opt_out": False}


async def _lead(db, p, **over):
    doc = {"company_id": p["company"]["id"], "source": "manual", "company_name": "Nuss GmbH", "country": "DE",
           "contact_name": "K W", "email": "k@nuss.de", "notes": "", "status": "sent", "is_demo": False,
           "is_hot": False, "score": 10, "source_note": "x"}
    doc.update(over)
    return str((await db.leads.insert_one(doc)).inserted_id)


def _llm(analysis=ANALYSIS, tr="Merhaba"):
    return lambda prompt: json.dumps(analysis if "reply_analyze" in prompt else {"text": tr})


async def _post(p, lid, text=GERMAN):
    return await p["client"].post(f"/api/leads/{lid}/reply", json={"text": text})


async def test_reply_german_interested_creates_draft(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm()
    lid = await _lead(db, p)
    r = await _post(p, lid)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["inbound"]["direction"] == "inbound" and j["inbound"]["status"] == "received"
    assert j["inbound"]["body"] == GERMAN and j["analysis"]["intent"] == "asks_samples"
    assert j["analysis"]["terms"]["incoterm"] == "FOB" and len(j["analysis"]["summary"]) == 3
    assert j["analysis"]["red_flags"] == ["urgency"]  # unknown LLM string dropped
    d = j["draft"]
    assert d["kind"] == "reply" and d["status"] == "draft" and d["language"] == "de" and d["body_tr"] == "Merhaba"
    assert (await db.leads.find_one({"company_id": p["company"]["id"]}))["status"] == "replied"
    assert_no_floor(j)


async def test_not_interested_sets_do_not_contact(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm({**ANALYSIS, "intent": "not_interested"})
    lid = await _lead(db, p)
    j = (await _post(p, lid, "Kein Interesse.")).json()
    assert j["draft"] is None
    assert (await db.leads.find_one({"company_id": p["company"]["id"]}))["status"] == "do_not_contact"
    assert await db.messages.count_documents({"status": "draft"}) == 0
    # opt_out flag alone does the same
    lid2 = await _lead(db, p, company_name="B")
    fake_llm.responses = _llm({**ANALYSIS, "opt_out": True})
    assert (await _post(p, lid2)).json()["draft"] is None
    # and further replies are refused before any LLM call
    n = len(fake_llm.prompts)
    r = await _post(p, lid2)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "do_not_contact" and len(fake_llm.prompts) == n


async def test_red_flag_heuristics_without_llm(db, producer, fake_llm):
    lead = {"email": "k@nuss.de"}
    assert detect_red_flags("Unsere Bankverbindung geändert, neues Konto IBAN DE89370400440532013000", lead) \
        == ["payment_change"]
    assert detect_red_flags("Please ship immediately, urgent", lead) == ["urgency"]
    assert detect_red_flags("Bitte Vorkasse 100% und sofort", lead) == ["urgency", "upfront_payment"]
    assert detect_red_flags("peşin %100 ödeme", lead) == ["upfront_payment"]
    assert detect_red_flags("%100 pamuk havlu istiyoruz", lead) == []
    assert detect_red_flags("write to boss@Gmail.com", lead) == ["domain_mismatch"]
    assert detect_red_flags("write to X@NUSS.de", lead) == []
    assert detect_red_flags("write to boss@gmail.com", {"email": ""}) == []
    # LLM down: heuristics still run, intent other, ack draft created, no analysis fake
    p = await producer("Ali")
    fake_llm.responses = lambda prompt: "garbage"
    lid = await _lead(db, p)
    j = (await _post(p, lid, "Dringend! Neues Konto: IBAN DE89 3704 0044 0532 0130 00")).json()
    a = j["analysis"]
    assert a["translation"] is None and a["summary"] == [] and a["intent"] == "other"
    assert a["red_flags"] == ["payment_change", "urgency"] and j["inbound"]["translation_fallback"] is True
    d = j["draft"]
    assert d["fallback"] is True and not has_amount(d["body"]) and "Angebot" in d["body"]
    # keyword opt-out still honoured without LLM
    lid2 = await _lead(db, p, company_name="C")
    j2 = (await _post(p, lid2, "Bitte nicht mehr kontaktieren")).json()
    assert j2["draft"] is None
    assert (await db.leads.find_one({"company_name": "C"}))["status"] == "do_not_contact"


async def test_reply_translation_in_ui_language(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm()
    lid = await _lead(db, p)
    await _post(p, lid)
    assert "ui_language: tr" in fake_llm.prompts[0]
    assert GERMAN in fake_llm.prompts[0]


async def test_summary_must_be_three_and_price_draft_falls_back(db, producer, fake_llm):
    p = await producer("Ali")
    lid = await _lead(db, p)
    fake_llm.responses = _llm({**ANALYSIS, "summary": ["a", "b"]})
    j = (await _post(p, lid)).json()
    assert j["analysis"]["summary"] == [] and j["analysis"]["intent"] == "other"  # invalid -> fallback
    fake_llm.responses = _llm({**ANALYSIS, "suggested_reply": {"subject": "Re", "body": "Preis 12,50 € pro kg."}})
    j = (await _post(p, lid)).json()
    assert j["draft"]["fallback"] is True and not has_amount(j["draft"]["body"])
    assert j["analysis"]["intent"] == "asks_samples"


async def test_reply_status_not_moved_backwards_and_ownership(db, producer, fake_llm):
    p, q = await producer("Ali"), await producer("Veli")
    fake_llm.responses = _llm()
    lid = await _lead(db, p, status="quoted")
    assert (await _post(p, lid)).status_code == 200
    assert (await db.leads.find_one({"company_id": p["company"]["id"]}))["status"] == "quoted"
    assert (await _post(q, lid)).status_code == 404
    assert (await p["client"].post(f"/api/leads/{lid}/reply", json={"text": "  "})).status_code == 422


async def test_reply_prompt_has_no_floor(db, producer, fake_llm):
    p = await producer("Ali")  # onboarding floor is 9.5
    fake_llm.responses = _llm()
    await _post(p, await _lead(db, p))
    assert "price_floor" not in fake_llm.prompts[0] and "9.5" not in fake_llm.prompts[0]


@pytest.mark.parametrize("text", ["Bitte kontaktieren Sie uns nicht mehr", "Lütfen bizimle iletisime gecmeyin",
                                  "Please do not contact us", "Bitte keine E-Mails mehr",
                                  "Please don’t contact us", "Bitte kontaktieren Sie mich nicht mehr",
                                  "Ich möchte mich nicht mehr kontaktieren lassen"])
async def test_explicit_optout_overrides_llm(db, producer, fake_llm, text):
    p = await producer("Ali")
    fake_llm.responses = _llm({**ANALYSIS, "intent": "interested", "opt_out": False})
    lid = await _lead(db, p)
    j = (await _post(p, lid, text)).json()
    assert j["draft"] is None and j["analysis"]["opt_out_source"] == "keyword"
    assert j["inbound"]["language"] in ("de", "en")
    assert (await db.leads.find_one({"company_id": p["company"]["id"]}))["status"] == "do_not_contact"


async def test_broad_phrase_not_blocked_when_llm_works(db, producer, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = _llm({**ANALYSIS, "intent": "interested"})
    j = (await _post(p, await _lead(db, p), "Kein Interesse an Salz, aber an Pistazien")).json()
    assert j["draft"] is not None and "opt_out_source" not in j["analysis"]
