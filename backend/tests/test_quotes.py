import io

import pytest
from pypdf import PdfReader

from app.services import storage_service as ss
from tests.helpers import assert_no_floor, load_kb_json


@pytest.fixture(autouse=True)
async def _rates(db, tmp_path):
    ss.set_root(tmp_path)
    await db.logistics_rates.insert_many(load_kb_json("logistics_rates"))
    yield
    ss.set_root(None)


def text(data: bytes) -> str:
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages).replace("​", "")


async def lead(p, country="DE"):
    r = await p["client"].post("/api/leads", json={"company_name": "Müller GmbH", "country": country,
                                                    "contact_name": "Hans", "source_note": "fair"})
    return r.json()["id"]


def body(p, lid, **over):
    b = {"lead_id": lid, "product_id": p["product"]["id"], "quantity": 500, "unit_price": 12.0, "currency": "EUR",
         "incoterm": "DAP", "payment_terms": "lc", "valid_until": "2099-12-31"}
    return {**b, **over}


async def make(p, lid=None, **over):
    lid = lid or await lead(p)
    return await p["client"].post("/api/quotes", json=body(p, lid, **over))


async def test_suggest_and_create_dap(producer):
    p = await producer("Ali")
    r = await p["client"].get(f"/api/quotes/suggest?product_id={p['product']['id']}")
    assert r.json() == {"unit_price": 11.88, "currency": "EUR"}
    r = await make(p)
    q = r.json()
    assert r.status_code == 201 and q["status"] == "draft" and q["freight_included"]
    assert q["logistics_estimate"]["freight_eur"] == 189.0 and q["total"] == 6189.0
    assert_no_floor(q)
    exw = (await make(p, incoterm="EXW")).json()
    assert exw["total"] == 6000.0 and not exw["freight_included"]


async def test_quote_below_floor_refused_without_number(producer):
    p = await producer("Ali")
    r = await make(p, unit_price=9.0)
    assert r.status_code == 422 and r.json()["detail"]["code"] == "below_floor"
    assert "9.5" not in r.text and "9,5" not in r.text
    assert (await make(p, unit_price=9.5)).status_code == 201


async def test_quote_error_codes(producer, db):
    p = await producer("Ali")
    lid = await lead(p)

    def code(r):
        return r.json()["detail"]["code"]

    assert code(await make(p, lid, quantity=0)) == "invalid_quantity"
    assert code(await make(p, lid, currency="USD")) == "floor_currency_mismatch"
    assert code(await make(p, lid, valid_until="2000-01-01")) == "invalid_valid_until"
    await db.products.update_one({}, {"$unset": {"unit_weight_kg": ""}})
    assert code(await make(p, lid)) == "needs_weight"
    r = await make(p, lid, unit_weight_kg=1)  # kept on the quote only
    assert r.status_code == 201 and r.json()["unit_weight_kg"] == 1
    assert "unit_weight_kg" not in await db.products.find_one({})
    assert code(await make(p, lid)) == "needs_weight"  # the earlier quote's weight is not reused
    await db.products.update_one({}, {"$set": {"price_floor_currency": "USD"}})
    assert code(await make(p, lid, currency="USD", unit_weight_kg=1)) == "freight_currency_mismatch"
    assert (await make(p, lid, currency="USD", incoterm="EXW", unit_weight_kg=1)).status_code == 201
    await db.leads.update_one({}, {"$set": {"status": "do_not_contact"}})
    assert code(await make(p, lid, currency="USD")) == "do_not_contact"


async def test_quote_not_sent_without_approval(producer, db):
    p = await producer("Ali")
    lid = await lead(p)
    q = (await make(p, lid)).json()
    assert (await db.quotes.find_one({}))["status"] == "draft"
    ap = (await p["client"].get("/api/approvals")).json()
    assert [x["id"] for x in ap["quotes"]] == [q["id"]]
    r = await p["client"].post(f"/api/quotes/{q['id']}/approve")
    assert r.status_code == 200 and r.json()["status"] == "sent" and r.json()["approved_by"]
    assert (await db.leads.find_one({}))["status"] == "quoted"
    assert (await p["client"].post(f"/api/quotes/{q['id']}/approve")).status_code == 409
    assert (await p["client"].get("/api/approvals")).json()["quotes"] == []


async def test_quote_pdf_german_no_floor(producer):
    p = await producer("Ali")
    q = (await make(p)).json()
    r = await p["client"].get(f"/api/quotes/{q['id']}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    t = text(r.content)
    for s in ("Angebot", "Gültig bis", "Zahlungsbedingungen", "geschätzt", "DAP", "Müller GmbH", "Bozkurt Gıda"):
        assert s in t, s
    for f in ("9.5", "9,5", "9,50", "9.50", "price_floor"):
        assert f not in t, f
    exw = (await make(p, incoterm="EXW")).json()
    assert "nicht enthalten" in text((await p["client"].get(f"/api/quotes/{exw['id']}/pdf")).content)


async def test_quote_preview_ui_language(producer):
    p = await producer("Ali")
    q = (await make(p)).json()
    t = text((await p["client"].get(f"/api/quotes/{q['id']}/pdf?preview=1")).content)
    assert "Teklif" in t and "Angebot" not in t and "tahmini" in t
    gb = (await make(p, await lead(p, "GB"))).json()
    assert "Quotation" in text((await p["client"].get(f"/api/quotes/{gb['id']}/pdf")).content)


async def test_quote_ownership(producer):
    a, b = await producer("Ali"), await producer("Veli")
    q = (await make(a)).json()
    for m, u in (("get", f"/api/quotes/{q['id']}"), ("post", f"/api/quotes/{q['id']}/approve"),
                 ("get", f"/api/quotes/{q['id']}/pdf")):
        assert (await getattr(b["client"], m)(u)).status_code == 404
    assert (await make(b, await lead(a))).status_code == 404  # foreign lead
    assert (await b["client"].get(f"/api/quotes/suggest?product_id={a['product']['id']}")).status_code == 404


async def test_rates_admin_only(producer, admin_client):
    p = await producer("Ali")
    assert (await p["client"].get("/api/admin/logistics-rates")).status_code == 403
    r = await admin_client.get("/api/admin/logistics-rates")
    rates = r.json()
    assert rates["packaging_pct"] == 0.08 and len(rates["ltl_bands"]) == 3
    rates["courier_min_eur"] = 70
    assert (await admin_client.put("/api/admin/logistics-rates", json=rates)).json()["courier_min_eur"] == 70
    rates["ltl_bands"][1]["max_kg"] = 100  # not ascending
    assert (await admin_client.put("/api/admin/logistics-rates", json=rates)).status_code == 422
    rates["ltl_bands"][1]["max_kg"] = 3000
    rates["ftl_eur_per_truck"] = -1
    assert (await admin_client.put("/api/admin/logistics-rates", json=rates)).status_code == 422


async def test_sample_task_created(producer):
    p = await producer("Ali")
    lid = await lead(p)
    r = await p["client"].post(f"/api/leads/{lid}/sample-task", json={"product_id": p["product"]["id"]})
    t = r.json()
    assert r.status_code == 201 and t["type"] == "numune_gonderimi"
    assert [c["key"] for c in t["checklist"]] == ["proforma", "labelling", "courier_booking"]
    assert t["courier_estimate"]["mode"] == "courier" and t["courier_estimate"]["freight_eur"] == 60.0
    assert len((await p["client"].get("/api/tasks")).json()) == 1
    for w in (0, 31):
        r = await p["client"].post(f"/api/leads/{lid}/sample-task",
                                   json={"product_id": p["product"]["id"], "sample_weight_kg": w})
        assert r.status_code == 422


@pytest.mark.parametrize("field", ["unit_price", "quantity"])
@pytest.mark.parametrize("bad", ["NaN", "Infinity", "-Infinity"])
async def test_nan_inf_rejected(producer, db, field, bad):
    p = await producer("Ali")
    lid = await lead(p)
    good = {"lead_id": lid, "product_id": p["product"]["id"], "quantity": "500", "unit_price": "12.0",
            "currency": '"EUR"', "incoterm": '"DAP"', "payment_terms": '"lc"', "valid_until": '"2099-12-31"'}
    good[field] = bad
    raw = "{" + ",".join(f'"{k}": {v if v[0] in "\"N-I0123456789" and k not in ("lead_id", "product_id") else chr(34) + v + chr(34)}'
                         for k, v in good.items()) + "}"
    r = await p["client"].post("/api/quotes", content=raw, headers={"content-type": "application/json"})
    assert r.status_code == 422 and await db.quotes.count_documents({}) == 0


async def test_nan_sample_weight_rejected(producer):
    p = await producer("Ali")
    lid = await lead(p)
    raw = '{"product_id": "%s", "sample_weight_kg": NaN}' % p["product"]["id"]
    r = await p["client"].post(f"/api/leads/{lid}/sample-task", content=raw,
                               headers={"content-type": "application/json"})
    assert r.status_code == 422


async def test_approve_failure_releases_claim(producer, db, monkeypatch):
    from app.services import outreach_service as svc

    p = await producer("Ali")
    q = (await make(p)).json()

    def boom(_doc):
        raise RuntimeError("boom")

    monkeypatch.setattr(svc, "assert_sent_has_approval", boom)
    with pytest.raises(RuntimeError):
        await p["client"].post(f"/api/quotes/{q['id']}/approve")
    d = await db.quotes.find_one({})
    assert d["status"] == "draft" and d["approved_at"] is None


async def test_approve_do_not_contact_and_sample_ownership(producer, db):
    a, b = await producer("Ali"), await producer("Veli")
    lid = await lead(a)
    q = (await make(a, lid)).json()
    await db.leads.update_one({}, {"$set": {"status": "do_not_contact"}})
    assert (await a["client"].post(f"/api/quotes/{q['id']}/approve")).status_code == 409
    url = f"/api/leads/{lid}/sample-task"
    assert (await a["client"].post(url, json={"product_id": a["product"]["id"]})).status_code == 409
    assert (await b["client"].post(url, json={"product_id": b["product"]["id"]})).status_code == 404
    lid2 = await lead(a)
    assert (await a["client"].post(f"/api/leads/{lid2}/sample-task",
                                   json={"product_id": b["product"]["id"]})).status_code == 404


class _FailLeadUpdate:
    """DB proxy (returned by a patched get_db): leads.update_one raises; everything else is the real db."""

    def __init__(self, real):
        self.real = real

    def __getattr__(self, name):
        coll = getattr(self.real, name)
        if name != "leads":
            return coll

        class Leads:
            def __getattr__(_self, n):
                return getattr(coll, n)

            async def update_one(_self, *a, **k):
                raise RuntimeError("lead update failed")

        return Leads()


async def test_quote_approve_lead_update_failure_reverts(producer, db, monkeypatch):
    from app.routers import quotes as qr

    p = await producer("Ali")
    q = (await make(p)).json()
    before = (await db.leads.find_one({}))["status"]
    monkeypatch.setattr(qr, "get_db", lambda: _FailLeadUpdate(db))
    with pytest.raises(RuntimeError):
        await p["client"].post(f"/api/quotes/{q['id']}/approve")
    d = await db.quotes.find_one({})
    assert d["status"] == "draft" and d["approved_at"] is None
    assert (await db.leads.find_one({}))["status"] == before
    monkeypatch.undo()
    assert (await p["client"].post(f"/api/quotes/{q['id']}/approve")).status_code == 200


async def test_message_approve_lead_update_failure_reverts(producer, db, monkeypatch):
    from app.routers import messages as mr

    p = await producer("Ali")
    lid = await lead(p)
    mid = (await db.messages.insert_one({"lead_id": lid, "company_id": p["company"]["id"], "direction": "outbound",
                                         "kind": "reply", "language": "de", "subject": "s", "body": "b",
                                         "status": "draft", "created_at": None})).inserted_id
    before = (await db.leads.find_one({}))["status"]
    monkeypatch.setattr(mr, "get_db", lambda: _FailLeadUpdate(db))
    with pytest.raises(RuntimeError):
        await p["client"].post(f"/api/messages/{mid}/approve")
    assert (await db.messages.find_one({}))["status"] == "draft"
    assert (await db.leads.find_one({}))["status"] == before


async def test_nan_sample_weight_stores_no_task(producer, db):
    p = await producer("Ali")
    lid = await lead(p)
    raw = '{"product_id": "%s", "sample_weight_kg": NaN}' % p["product"]["id"]
    r = await p["client"].post(f"/api/leads/{lid}/sample-task", content=raw,
                               headers={"content-type": "application/json"})
    assert r.status_code == 422 and await db.tasks.count_documents({}) == 0


async def test_quote_reject_and_ownership(producer):
    a, b = await producer("Ali"), await producer("Veli")
    q = (await make(a)).json()
    assert (await b["client"].post(f"/api/quotes/{q['id']}/reject", json={"reason": "x"})).status_code == 404
    assert (await a["client"].post(f"/api/quotes/{q['id']}/reject", json={"reason": ""})).status_code == 422
    r = await a["client"].post(f"/api/quotes/{q['id']}/reject", json={"reason": "wrong price"})
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    assert (await a["client"].post(f"/api/quotes/{q['id']}/reject", json={"reason": "again"})).status_code == 409
    assert (await a["client"].post(f"/api/quotes/{q['id']}/approve")).status_code == 409
    assert (await a["client"].get("/api/approvals")).json()["quotes"] == []


async def test_pipeline_stats_real_counts_own_company(producer, db):
    a, b = await producer("Ali"), await producer("Veli")
    assert (await a["client"].get("/api/pipeline/stats")).json() == {
        "leads": 0, "messages_sent": 0, "replies": 0, "quotes_sent": 0, "won": 0}
    lid = await lead(a)
    await lead(b)
    cid = (await db.leads.find_one({}))["company_id"]
    await db.messages.insert_many([
        {"lead_id": lid, "company_id": cid, "direction": "outbound", "status": "sent"},
        {"lead_id": lid, "company_id": cid, "direction": "outbound", "status": "draft"},
        {"lead_id": lid, "company_id": cid, "direction": "inbound", "status": "sent"}])
    q = (await make(a, lid)).json()
    await a["client"].post(f"/api/quotes/{q['id']}/approve")
    await a["client"].patch(f"/api/leads/{lid}", json={"status": "won"})
    assert (await a["client"].get("/api/pipeline/stats")).json() == {
        "leads": 1, "messages_sent": 1, "replies": 1, "quotes_sent": 1, "won": 1}


async def test_quote_pdf_freight_text_locale(producer):
    p = await producer("Ali")
    q = (await make(p)).json()
    de = text((await p["client"].get(f"/api/quotes/{q['id']}/pdf")).content)
    assert de.count("geschätzt") == 1 and "unverbindlich" in de
    assert "bis 3.000 kg" in de and "0,35 EUR/kg" in de and "0.35" not in de and "≤" not in de
    gb = (await make(p, await lead(p, "GB"))).json()
    en = text((await p["client"].get(f"/api/quotes/{gb['id']}/pdf")).content)
    assert "0.35 EUR/kg" in en and "up to 3,000 kg" in en and en.count("estimated") == 1
    tr = text((await p["client"].get(f"/api/quotes/{q['id']}/pdf?preview=1")).content)
    assert "0,35 EUR/kg" in tr and "3.000 kg'a kadar" in tr and tr.count("(tahmini, bağlayıcı değil)") == 1 and "tahmini) (" not in tr
    assert q["logistics_estimate"]["lines"][1]["values"]["rate"] == 0.35
