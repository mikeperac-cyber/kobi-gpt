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
    r = await make(p, lid, unit_weight_kg=1)  # saved to the product
    assert r.status_code == 201 and (await db.products.find_one({}))["unit_weight_kg"] == 1
    await db.products.update_one({}, {"$set": {"price_floor_currency": "USD"}})
    assert code(await make(p, lid, currency="USD")) == "freight_currency_mismatch"
    assert (await make(p, lid, currency="USD", incoterm="EXW")).status_code == 201
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
