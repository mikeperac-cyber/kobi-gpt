from app.core.config import get_settings


async def test_health_reports_provider_without_key(client, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-secret-123")
    get_settings.cache_clear()
    r = await client.get("/api/health")
    body = r.json()
    assert r.status_code == 200
    assert body == {"status": "ok", "llm": {"provider": "anthropic", "key_set": True}}
    assert "sk-secret-123" not in r.text
    get_settings.cache_clear()


def test_to_json():
    from datetime import datetime
    from bson import ObjectId
    from app.core.serialize import to_json

    oid = ObjectId()
    out = to_json({"_id": oid, "owner": oid, "at": datetime(2026, 1, 2, 3, 4, 5), "n": 1, "sub": [{"_id": oid}]})
    assert out == {"id": str(oid), "owner": str(oid), "at": "2026-01-02T03:04:05", "n": 1, "sub": [{"id": str(oid)}]}
