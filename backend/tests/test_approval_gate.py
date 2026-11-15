import json
from datetime import datetime, timedelta, timezone

import pytest

from app.services.outreach_service import assert_sent_has_approval
from tests.test_outreach import _lead, _llm


async def _draft(db, p, **over):
    lid = await _lead(db, p, **over)
    r = await p["client"].post(f"/api/leads/{lid}/draft", json={})
    assert r.status_code == 201, r.text
    return lid, r.json()["id"]


async def test_approve_records_approval_and_updates_lead(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    lid, mid = await _draft(db, p)
    r = await p["client"].post(f"/api/messages/{mid}/approve")
    assert r.status_code == 200
    m = r.json()
    assert m["status"] == "sent" and m["approved_by"] == p["user"]["id"] and m["approved_at"]
    assert m["delivery_channel"] == "mailto"
    from bson import ObjectId
    assert (await db.leads.find_one({"_id": ObjectId(lid)}))["status"] == "sent"
    assert (await p["client"].post(f"/api/messages/{mid}/approve")).status_code == 409  # not twice


async def test_no_sent_without_approval_fields(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    c = p["client"]
    ids = [(await _draft(db, p))[1] for _ in range(3)]
    await c.post(f"/api/messages/{ids[0]}/approve")
    await c.post(f"/api/messages/{ids[1]}/reject", json={"reason": "nope"})
    for mid in ids:  # PUT cannot smuggle status / approval fields
        r = await c.put(f"/api/messages/{mid}", json={"subject": "s", "body": "b", "status": "sent",
                                                      "approved_by": "x"})
        assert r.status_code == 422
    r = await c.put(f"/api/messages/{ids[2]}", json={"subject": "s", "body": "ok."})
    assert r.status_code == 200 and r.json()["status"] == "draft"
    assert (await c.put(f"/api/messages/{ids[0]}", json={"subject": "s", "body": "ok."})).status_code == 409
    await c.get("/api/approvals")
    sent = [m async for m in db.messages.find({"status": "sent"})]
    assert len(sent) == 1
    for m in sent:
        assert m["approved_by"] and m["approved_at"] and m["delivery_channel"]
    with pytest.raises(RuntimeError):
        assert_sent_has_approval({"status": "sent", "approved_by": None})


async def test_reject(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    _, mid = await _draft(db, p)
    c = p["client"]
    assert (await c.post(f"/api/messages/{mid}/reject", json={"reason": ""})).status_code == 422
    r = await c.post(f"/api/messages/{mid}/reject", json={"reason": "zu allgemein"})
    assert r.json()["status"] == "rejected" and r.json()["reject_reason"] == "zu allgemein"
    assert (await c.post(f"/api/messages/{mid}/approve")).status_code == 409


async def test_daily_limit_20(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    ids = [(await _draft(db, p, email=f"a{i}@x.de"))[1] for i in range(21)]
    for mid in ids[:20]:
        assert (await p["client"].post(f"/api/messages/{mid}/approve")).status_code == 200
    r = await p["client"].post(f"/api/messages/{ids[20]}/approve")
    assert r.status_code == 429 and r.json()["detail"]["code"] == "daily_limit"
    assert (await db.messages.find_one({"_id": __import__("bson").ObjectId(ids[20])}))["status"] == "draft"
    # yesterday's approvals do not count; rfq answers are exempt
    await db.messages.update_many({"status": "sent"}, {"$set": {"approved_at": datetime.now(timezone.utc)
                                                                - timedelta(days=1, minutes=1)}})
    assert (await p["client"].post(f"/api/messages/{ids[20]}/approve")).status_code == 200


async def test_rfq_answers_not_limited(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    ids = [(await _draft(db, p, source="rfq", notes="hi"))[1] for _ in range(21)]
    for mid in ids:
        assert (await p["client"].post(f"/api/messages/{mid}/approve")).status_code == 200


async def test_do_not_contact_blocks_approval(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    lid, mid = await _draft(db, p)
    await p["client"].patch(f"/api/leads/{lid}", json={"status": "do_not_contact"})
    r = await p["client"].post(f"/api/messages/{mid}/approve")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "do_not_contact"


async def test_approvals_list_and_dashboard_count(db, producer, fake_llm):
    fake_llm.responses = _llm()
    p = await producer("Ali")
    await _draft(db, p, is_demo=True)
    r = (await p["client"].get("/api/approvals")).json()
    assert len(r["messages"]) == 1 and r["quotes"] == []
    assert r["messages"][0]["lead"]["company_name"] == "Nuss GmbH" and r["messages"][0]["lead"]["is_demo"] is True
    assert (await p["client"].get("/api/dashboard")).json()["leads"]["pending_approvals"] == 1


async def test_approvals_ownership(db, producer, fake_llm):
    fake_llm.responses = _llm()
    a, b = await producer("Ali"), await producer("Veli")
    lid, mid = await _draft(db, a)
    c = b["client"]
    assert (await c.get("/api/approvals")).json()["messages"] == []
    assert (await c.post(f"/api/leads/{lid}/draft", json={})).status_code == 404
    assert (await c.put(f"/api/messages/{mid}", json={"subject": "s", "body": "b"})).status_code == 404
    assert (await c.post(f"/api/messages/{mid}/approve")).status_code == 404
    assert (await c.post(f"/api/messages/{mid}/reject", json={"reason": "x"})).status_code == 404
    assert (await db.messages.find_one({}))["status"] == "draft"


async def test_reject_resets_lead_status(db, producer, fake_llm):
    from bson import ObjectId
    fake_llm.responses = _llm()
    p = await producer("Ali")
    lid, mid = await _draft(db, p)
    await p["client"].post(f"/api/messages/{mid}/reject", json={"reason": "x"})
    assert (await db.leads.find_one({"_id": ObjectId(lid)}))["status"] == "new"


async def test_failed_provider_releases_claim(db, producer, fake_llm, monkeypatch):
    from app.services import outreach_service as o

    class Boom:
        async def send(self, *a):
            raise RuntimeError("smtp down")

    monkeypatch.setattr(o, "get_email_provider", lambda: Boom())
    monkeypatch.setenv("EMAIL_PROVIDER", "x")
    from app.core.config import get_settings
    get_settings.cache_clear()
    fake_llm.responses = _llm()
    p = await producer("Ali")
    _, mid = await _draft(db, p)
    with pytest.raises(RuntimeError):
        await p["client"].post(f"/api/messages/{mid}/approve")
    m = await db.messages.find_one({})
    assert m["status"] == "draft" and m["approved_at"] is None
