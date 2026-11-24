from datetime import date, timedelta

import pytest

from app.services import storage_service as ss

PDF = b"%PDF-1.4 1 0 obj<<>>endobj trailer<<>> %%EOF"
NEXT_YEAR = (date.today() + timedelta(days=365)).isoformat()


@pytest.fixture(autouse=True)
def _root(tmp_path):
    ss.set_root(tmp_path)
    yield
    ss.set_root(None)


async def _doc(c) -> str:
    r = await c.post("/api/uploads/document", files={"file": ("cert.pdf", PDF, "application/pdf")})
    assert r.status_code == 200, r.text
    return r.json()["url"]


async def _submit(c, kind="certificate", name="ISO 22000", valid_until=NEXT_YEAR, file_url=None):
    body = {"kind": kind, "name": name, "issuer": "TSE", "valid_until": valid_until,
            "file_url": file_url or await _doc(c)}
    return await c.post("/api/verifications", json=body)


def _code(r):
    return r.json()["detail"]["code"]


async def test_submit_and_verify_lifecycle(producer, admin_client):
    p = await producer("Ali")
    r = await _submit(p["client"])
    assert r.status_code == 201 and r.json()["status"] == "pending"
    vid = r.json()["id"]
    pending = (await admin_client.get("/api/admin/verifications")).json()
    assert [v["id"] for v in pending] == [vid] and pending[0]["company_name"] == "Bozkurt Gıda"
    f = await admin_client.get(f"/api/admin/verifications/{vid}/file")
    assert f.status_code == 200 and f.headers["content-type"] == "application/pdf" and f.content == PDF
    assert (await admin_client.post(f"/api/admin/verifications/{vid}/verify")).status_code == 200
    mine = (await p["client"].get("/api/verifications")).json()
    assert mine[0]["status"] == "verified" and mine[0]["reviewed_at"]


async def test_certificate_name_must_be_in_profile(producer):
    p = await producer("Ali")
    r = await _submit(p["client"], name="ISO 9001")
    assert r.status_code == 422 and _code(r) == "unknown_certificate"
    r = await _submit(p["client"], name="iso 22000")  # folded match with the profile's "ISO 22000"
    assert r.status_code == 201


async def test_tax_plate_needs_no_name(producer):
    p = await producer("Ali")
    r = await _submit(p["client"], kind="tax_plate", name="", valid_until=None)
    assert r.status_code == 201 and r.json()["name"] == "tax_plate"


async def test_expired_document_rejected(producer):
    p = await producer("Ali")
    r = await _submit(p["client"], valid_until=(date.today() - timedelta(days=1)).isoformat())
    assert r.status_code == 422 and _code(r) == "expired_document"


async def test_file_must_be_a_private_document(producer):
    p = await producer("Ali")
    r = await _submit(p["client"], file_url="/uploads/products/a.webp")  # owned, but a public product photo
    assert r.status_code == 422 and _code(r) == "bad_document"


async def test_resubmit_replaces_pending_and_rejected_not_verified(producer, admin_client):
    p = await producer("Ali")
    c = p["client"]
    first = (await _submit(c)).json()["id"]
    second = (await _submit(c)).json()["id"]  # replaces the pending one
    ids = [v["id"] for v in (await c.get("/api/verifications")).json()]
    assert ids == [second]
    await admin_client.post(f"/api/admin/verifications/{second}/verify")
    third = (await _submit(c, name="ISO 22000")).json()["id"]  # renewal: the verified one stays
    assert {v["id"] for v in (await c.get("/api/verifications")).json()} == {second, third}
    assert first not in ids


async def test_admin_only(producer):
    p = await producer("Ali")
    assert (await p["client"].get("/api/admin/verifications")).status_code == 403


async def test_other_company_cannot_touch(producer):
    a, b = await producer("Ali"), await producer("Veli")
    vid = (await _submit(a["client"])).json()["id"]
    assert (await b["client"].delete(f"/api/verifications/{vid}")).status_code == 404
    assert (await a["client"].delete(f"/api/verifications/{vid}")).status_code == 200


async def test_reject_needs_reason_and_pending(producer, admin_client):
    p = await producer("Ali")
    vid = (await _submit(p["client"])).json()["id"]
    assert (await admin_client.post(f"/api/admin/verifications/{vid}/reject", json={"reason": ""})).status_code == 422
    r = await admin_client.post(f"/api/admin/verifications/{vid}/reject", json={"reason": "Okunmuyor"})
    assert r.status_code == 200
    assert (await p["client"].get("/api/verifications")).json()[0]["reject_reason"] == "Okunmuyor"
    r = await admin_client.post(f"/api/admin/verifications/{vid}/verify")
    assert r.status_code == 409 and _code(r) == "not_pending"
    assert (await p["client"].delete(f"/api/verifications/{vid}")).status_code == 409


async def _publish(db, p, slug="ali-shop"):
    from tests.helpers import publishable_site_config
    await db.storefronts.insert_one({"company_id": p["company"]["id"], "country": "DE", "slug": slug,
                                     "status": "published", "template": "natural",
                                     "site_config": publishable_site_config()})
    return f"/api/public/storefronts/{slug}"


async def _verified(p, admin_client, **kw) -> str:
    vid = (await _submit(p["client"], **kw)).json()["id"]
    assert (await admin_client.post(f"/api/admin/verifications/{vid}/verify")).status_code == 200
    return vid


async def test_public_trust_labels(producer, admin_client, db, client):
    p = await producer("Ali")
    url = await _publish(db, p)
    await _verified(p, admin_client, name="iso 22000")  # folded match
    trust = (await client.get(url)).json()["company"]["trust"]
    assert trust["company_verified"] is False and trust["verified_at"] is None
    assert trust["certificates"] == [{"name": "ISO 22000", "verified": True, "valid_until": NEXT_YEAR},
                                     {"name": "IATF 16949", "verified": False, "valid_until": None}]
    await _verified(p, admin_client, kind="tax_plate", name="", valid_until=None)
    trust = (await client.get(url)).json()["company"]["trust"]
    assert trust["company_verified"] is True and trust["verified_at"] == date.today().isoformat()


async def test_public_trust_expiry(producer, admin_client, db, client):
    p = await producer("Ali")
    url = await _publish(db, p)
    await _verified(p, admin_client)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    await db.verifications.update_many({}, {"$set": {"valid_until": yesterday}})
    cert = (await client.get(url)).json()["company"]["trust"]["certificates"][0]
    assert cert == {"name": "ISO 22000", "verified": False, "valid_until": None}


async def test_public_trust_follows_profile(producer, admin_client, db, client):
    from bson import ObjectId
    p = await producer("Ali")
    url = await _publish(db, p)
    await _verified(p, admin_client)
    await db.companies.update_one({"_id": ObjectId(p["company"]["id"])}, {"$set": {"certifications": ["IATF 16949"]}})
    certs = (await client.get(url)).json()["company"]["trust"]["certificates"]
    assert [c["name"] for c in certs] == ["IATF 16949"]


async def test_public_payload_trust_has_no_private_fields(producer, admin_client, db, client):
    p = await producer("Ali")
    url = await _publish(db, p)
    await _verified(p, admin_client)
    await _verified(p, admin_client, kind="tax_plate", name="", valid_until=None)
    r = await client.get(url)
    trust = r.json()["company"]["trust"]
    assert set(trust) == {"company_verified", "verified_at", "certificates"}
    assert all(set(c) == {"name", "verified", "valid_until"} for c in trust["certificates"])
    assert "/uploads/documents" not in r.text and "reviewed_by" not in r.text
