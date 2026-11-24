import io

from tests.helpers import assert_no_floor  # noqa: F401

RFQ = {"company_name": "Nussgarten GmbH", "contact_name": "K W", "email": "k@nuss.de", "country": "DE",
       "products": ["Pistazien"], "quantity": "1 t", "message": "Wir suchen Pistazien", "gdpr_consent": True}
NEW = {"company_name": "Manuell GmbH", "country": "de", "email": "m@x.de", "source_note": "Messe Köln 2026"}


async def _publish(db, p):
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "slug": "s1", "status": "published",
                                     "site_config": {"de": {}, "en": {}}, "country": "DE"})


async def test_rfq_lead_scored_on_create(db, producer, client):
    p = await producer("Ali")
    await _publish(db, p)
    assert (await client.post("/api/public/storefronts/s1/rfq", json=RFQ)).status_code == 201
    lead = await db.leads.find_one({"company_id": p["company"]["id"]})
    assert lead["score"] == 40 + 15 + 15 + 10 and lead["score_breakdown"]["source"] == 40


async def test_manual_requires_source_note(producer):
    c = (await producer("Ali"))["client"]
    for bad in ({k: v for k, v in NEW.items() if k != "source_note"}, {**NEW, "source_note": "  "}):
        r = await c.post("/api/leads", json=bad)
        assert r.status_code == 422 and r.json()["detail"]["code"] == "source_note_required"
    r = await c.post("/api/leads", json=NEW)
    assert r.status_code == 201 and r.json()["country"] == "DE" and r.json()["source"] == "manual"
    assert r.json()["score"] == 15 + 15 + 15


def _prev(c, data):
    return c.post("/api/leads/import/preview", files={"file": ("l.csv", io.BytesIO(data), "text/csv")})


MAP = {"company_name": "Firma", "country": "Land", "email": "Mail"}


async def test_csv_import_requires_source_note(producer):
    c = (await producer("Ali"))["client"]
    fid = (await _prev(c, b"Firma,Land\nA GmbH,DE\n")).json()["file_id"]
    r = await c.post("/api/leads/import", json={"file_id": fid, "mapping": MAP, "source_note": ""})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "source_note_required"


async def test_csv_import_bom_cp1254_semicolon(producer, db):
    p = await producer("Ali")
    c = p["client"]
    data = "Firma;Land;Mail\nŞahin Handels GmbH;DE;s@sahin.de\nŞahin Handels GmbH;DE;S@sahin.de\nBad;DEU;x\n;DE;\n"
    pv = (await _prev(c, data.encode("cp1254"))).json()
    assert pv["headers"] == ["Firma", "Land", "Mail"] and pv["rows"][0][0] == "Şahin Handels GmbH"
    r = await c.post("/api/leads/import", json={"file_id": pv["file_id"], "mapping": MAP, "source_note": "Messe"})
    body = r.json()
    assert body["imported"] == 1 and body["skipped"] == 3 and len(body["errors"]) == body["skipped"]
    assert body["errors"] == [{"row": 3, "reason": "duplicate"}, {"row": 4, "reason": "bad_country"},
                              {"row": 5, "reason": "no_company_name"}]
    lead = await db.leads.find_one({"company_name": "Şahin Handels GmbH"})
    assert lead["source"] == "csv_import" and lead["source_note"] == "Messe" and lead["score"] == 20 + 15 + 15
    assert await db.lead_imports.count_documents({}) == 0
    pv = (await _prev(c, b"\xef\xbb\xbf" + "Firma,Land\nMüller GmbH,DE\n".encode())).json()
    assert pv["rows"][0][0] == "Müller GmbH"


async def test_csv_formula_guard_and_size(producer):
    c = (await producer("Ali"))["client"]
    pv = (await _prev(c, b"Firma\n'=cmd\n")).json()
    assert pv["rows"][0][0] == "=cmd"
    r = await _prev(c, b"a" * (2 * 1024 * 1024 + 1))
    assert r.status_code == 413 and r.json()["detail"]["code"] == "file_too_large"


async def test_leads_ownership(producer):
    a, b = await producer("Ali"), await producer("Veli")
    lid = (await a["client"].post("/api/leads", json=NEW)).json()["id"]
    assert [x["id"] for x in (await a["client"].get("/api/leads")).json()] == [lid]
    assert (await b["client"].get("/api/leads")).json() == []
    assert (await b["client"].get(f"/api/leads/{lid}")).status_code == 404
    assert (await b["client"].patch(f"/api/leads/{lid}", json={"status": "won"})).status_code == 404
    fid = (await _prev(a["client"], b"Firma\nA\n")).json()["file_id"]
    r = await b["client"].post("/api/leads/import", json={"file_id": fid, "mapping": {"company_name": "Firma"},
                                                          "source_note": "x"})
    assert r.status_code == 404


async def test_default_sort_rfq_first(db, producer, client):
    p = await producer("Ali")
    c = p["client"]
    await _publish(db, p)
    await c.post("/api/leads", json={**NEW, "company_name": "High", "email": "h@x.de", "notes": "pistazien fistik"})
    await client.post("/api/public/storefronts/s1/rfq", json={**RFQ, "email": "r@x.fr", "country": "FR", "message": "hi"})
    names = [x["company_name"] for x in (await c.get("/api/leads")).json()]
    assert names == ["Nussgarten GmbH", "High"]
    newest = [x["company_name"] for x in (await c.get("/api/leads?sort=created_at")).json()]
    assert newest == ["Nussgarten GmbH", "High"]  # explicit sort is pure (RFQ happens to be newest)
    assert len((await c.get("/api/leads?sort=score")).json()) == 2
    assert len((await c.get("/api/leads?status=won")).json()) == 0


async def test_status_rules(producer):
    c = (await producer("Ali"))["client"]
    lid = (await c.post("/api/leads", json=NEW)).json()["id"]
    r = await c.patch(f"/api/leads/{lid}", json={"status": "sent"})
    assert r.status_code == 422
    r = await c.patch(f"/api/leads/{lid}", json={"status": "bogus"})
    assert r.status_code == 422
    assert (await c.patch(f"/api/leads/{lid}", json={"status": "do_not_contact"})).json()["status"] == "do_not_contact"
    r = await c.patch(f"/api/leads/{lid}", json={"status": "new"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "lead_blocked"


async def test_csv_import_country_defaults_to_market(producer, db):
    c = (await producer("Ali"))["client"]
    pv = (await _prev(c, b"Firma,Mail"+bytes([10])+b"A GmbH,a@a.de"+bytes([10])+b"B GmbH,b@b.de"+bytes([10]))).json()
    r = await c.post("/api/leads/import", json={"file_id": pv["file_id"], "mapping": {"company_name": "Firma", "email": "Mail"},
                                                "source_note": "x"})
    assert r.json() == {"imported": 2, "skipped": 0, "errors": []}
    assert {d["country"] async for d in db.leads.find({})} == {"DE"}


async def test_status_filter_validated(producer):
    c = (await producer("Ali"))["client"]
    assert (await c.get("/api/leads?status=bogus")).status_code == 422


async def _three(db, cid):
    from datetime import datetime, timezone
    docs = [{"company_name": "A", "score": 50, "is_hot": False, "created_at": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"company_name": "B", "score": 90, "is_hot": False, "created_at": datetime(2026, 1, 2, tzinfo=timezone.utc)},
            {"company_name": "C", "score": 10, "is_hot": True, "created_at": datetime(2026, 1, 3, tzinfo=timezone.utc)}]
    await db.leads.insert_many([{**d, "company_id": cid, "status": "new", "country": "DE"} for d in docs])


async def test_list_leads_db_sort_and_pages(producer, db):
    p = await producer("Ali")
    c = p["client"]
    await _three(db, p["company"]["id"])
    names = lambda r: [x["company_name"] for x in r.json()]  # noqa: E731
    assert names(await c.get("/api/leads")) == ["C", "B", "A"]  # hot first, then score
    assert names(await c.get("/api/leads?sort=score")) == ["B", "A", "C"]
    assert names(await c.get("/api/leads?sort=created_at")) == ["C", "B", "A"]
    r = await c.get("/api/leads?limit=2")
    assert names(r) == ["C", "B"] and r.headers["x-total-count"] == "3"
    assert names(await c.get("/api/leads?limit=2&offset=2")) == ["A"]
    assert (await c.get("/api/leads?limit=501")).status_code == 422
    assert len((await c.get("/api/leads?sort=score&limit=500")).json()) == 3  # pipeline page request


async def test_total_count_header_exposed_to_browser(client):
    r2 = await client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert "x-total-count" in r2.headers.get("access-control-expose-headers", "").lower()


async def test_won_requires_deal_value(producer, db):
    p = await producer("Ali")
    c = p["client"]
    lid = (await c.post("/api/leads", json={"company_name": "Müller GmbH", "country": "DE",
                                            "source_note": "fair"})).json()["id"]
    url = f"/api/leads/{lid}"
    r = await c.patch(url, json={"status": "won"})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "deal_value_required"
    for bad in (0, -5, 1e12):
        assert (await c.patch(url, json={"status": "won", "deal_value": bad, "deal_currency": "EUR"})).status_code == 422
    raw = '{"status": "won", "deal_value": NaN, "deal_currency": "EUR"}'
    assert (await c.patch(url, content=raw, headers={"Content-Type": "application/json"})).status_code == 422
    assert (await c.patch(url, json={"status": "won", "deal_value": 5, "deal_currency": "GBP"})).status_code == 422
    r = await c.patch(url, json={"status": "won", "deal_value": 12500, "deal_currency": "EUR"})
    assert r.status_code == 200 and r.json()["deal_value"] == 12500 and r.json()["deal_currency"] == "EUR"
    assert r.json()["won_at"]


async def test_lost_ignores_deal_fields(producer, db):
    p = await producer("Ali")
    c = p["client"]
    lid = (await c.post("/api/leads", json={"company_name": "Müller GmbH", "country": "DE",
                                            "source_note": "fair"})).json()["id"]
    r = await c.patch(f"/api/leads/{lid}", json={"status": "lost", "deal_value": 100, "deal_currency": "EUR"})
    assert r.status_code == 200 and "deal_value" not in r.json()
