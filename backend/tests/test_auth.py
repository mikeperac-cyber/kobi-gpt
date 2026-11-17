import pytest
REG = {"name": "Ali", "email": "ali@firma.com", "password": "password123", "kvkk_consent": True}


async def test_register_requires_kvkk(client):
    r = await client.post("/api/auth/register", json={**REG, "kvkk_consent": False})
    assert r.status_code == 422


async def test_password_min_8(client):
    r = await client.post("/api/auth/register", json={**REG, "password": "short"})
    assert r.status_code == 422


async def test_register_login_logout_cycle(client):
    r = await client.post("/api/auth/register", json=REG)
    assert r.status_code == 201
    assert "password_hash" not in r.text and r.json()["ui_language"] == "tr"
    assert (await client.get("/api/auth/me")).status_code == 200
    assert (await client.post("/api/auth/logout")).status_code == 200
    assert (await client.get("/api/auth/me")).status_code == 401
    r = await client.post("/api/auth/login", json={"email": REG["email"], "password": REG["password"]})
    assert r.status_code == 200
    me = (await client.get("/api/auth/me")).json()
    assert me["has_company"] is False and me["email"] == "ali@firma.com"


async def test_email_is_case_insensitive(client):
    await client.post("/api/auth/register", json={**REG, "email": " Ali@Firma.com "})
    await client.post("/api/auth/logout")
    r = await client.post("/api/auth/login", json={"email": "ali@firma.com", "password": REG["password"]})
    assert r.status_code == 200
    r = await client.post("/api/auth/register", json={**REG, "email": "ALI@firma.com"})
    assert r.status_code == 409 and r.json()["detail"]["code"] == "email_taken"


async def test_ui_language_persists_across_login(client):
    await client.post("/api/auth/register", json=REG)
    assert (await client.patch("/api/auth/me", json={"ui_language": "en"})).status_code == 200
    assert (await client.patch("/api/auth/me", json={"ui_language": "de"})).status_code == 422
    await client.post("/api/auth/logout")
    await client.post("/api/auth/login", json={"email": REG["email"], "password": REG["password"]})
    assert (await client.get("/api/auth/me")).json()["ui_language"] == "en"


async def test_auth_rate_limit(client):
    bad = {"email": "x@y.com", "password": "wrongpass1"}
    codes = [(await client.post("/api/auth/login", json=bad)).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429


async def test_cookie_flags(client):
    r = await client.post("/api/auth/register", json=REG)
    c = r.headers["set-cookie"].lower()
    assert "kobi_session=" in c and "httponly" in c and "samesite=lax" in c


async def test_non_admin_forbidden(client):
    await client.post("/api/auth/register", json=REG)
    assert (await client.post("/api/admin/llm-test")).status_code == 403


async def test_password_too_long_bytes(client):
    pw = "şğı" * 13 + "ab"  # 41 chars, 80 bytes
    r = await client.post("/api/auth/register", json={**REG, "password": pw})
    assert r.status_code == 422
    from app.core.security import verify_password

    assert verify_password(pw, "$2b$12$" + "a" * 53) is False
    r = await client.post("/api/auth/login", json={"email": REG["email"], "password": pw})
    assert r.status_code == 401


async def test_wrong_password_and_tampered_token(client):
    await client.post("/api/auth/register", json=REG)
    r = await client.post("/api/auth/login", json={"email": REG["email"], "password": "nopenope1"})
    assert r.status_code == 401
    client.cookies.set("kobi_session", client.cookies["kobi_session"][:-3] + "abc")
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_unique_email_index_race(client, db):
    from pymongo.errors import DuplicateKeyError
    import pytest

    await db.users.insert_one({"email": "a@b.com"})
    with pytest.raises(DuplicateKeyError):
        await db.users.insert_one({"email": "a@b.com"})


async def test_insecure_secret_guard(monkeypatch):
    import pytest
    from app.core.config import get_settings
    from app.main import create_app

    monkeypatch.setenv("JWT_SECRET", "dev-secret-change-me")
    monkeypatch.setenv("FRONTEND_ORIGIN", "https://kobi.example.com")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        create_app()


@pytest.mark.parametrize("origin,secret,bad", [
    ("https://kobi.example.com", "change-me", True),
    ("https://kobi.example.com", "", True),
    ("https://kobi.example.com", "short-but-not-weak", True),
    ("http://localhost.evil.com", "x" * 40, False),
    ("http://localhost.evil.com", "change-me", True),
    ("https://kobi.example.com", "x" * 40, False),
    ("http://localhost:5173", "dev-secret-change-me", False),
])
def test_jwt_secret_guard(origin, secret, bad):
    from types import SimpleNamespace
    from app.main import check_jwt_secret

    s = SimpleNamespace(frontend_origin=origin, jwt_secret=secret)
    if bad:
        with pytest.raises(RuntimeError):
            check_jwt_secret(s)
    else:
        check_jwt_secret(s)
