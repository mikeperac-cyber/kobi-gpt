import io

import pytest
from PIL import Image

from app.services import storage_service as ss

REG = {"name": "Ali", "email": "ali@firma.com", "password": "password123", "kvkk_consent": True}


@pytest.fixture(autouse=True)
def _tmp_root(tmp_path):
    ss.set_root(tmp_path)
    yield tmp_path
    ss.set_root(None)


def _img(fmt, mode="RGB", size=(40, 30)):
    buf = io.BytesIO()
    Image.new(mode, size, "red" if mode in ("RGB", "RGBA") else 0).save(buf, fmt)
    return buf.getvalue()


def test_rejects_renamed_text_file():
    with pytest.raises(ValueError, match="bad_type"):
        ss.validate_and_process_image(b"hello")


def test_rejects_corrupt_jpeg_with_valid_signature():
    with pytest.raises(ValueError, match="bad_type"):
        ss.validate_and_process_image(b"\xff\xd8\xff" + b"garbage")


def test_rejects_over_8mb():
    with pytest.raises(ValueError, match="too_large"):
        ss.validate_and_process_image(b"\xff\xd8\xff" + b"0" * (8 * 1024 * 1024))


def test_resizes_large_png():
    out = ss.validate_and_process_image(_img("PNG", size=(2400, 1200)))
    assert out.startswith(b"RIFF")
    assert max(Image.open(io.BytesIO(out)).size) == 1600


def test_converts_cmyk_jpeg_and_rgba_png():
    for data in (_img("JPEG", "CMYK"), _img("PNG", "RGBA"), _img("PNG", "P"), _img("WEBP")):
        assert ss.validate_and_process_image(data).startswith(b"RIFF")


async def test_save_and_delete(tmp_path):
    st = ss.get_storage()
    url = await st.save(ss.validate_and_process_image(_img("PNG")), "products")
    assert url.startswith("/uploads/products/") and url.endswith(".webp")
    assert (tmp_path / url.removeprefix("/uploads/")).exists()
    await st.delete(url)
    assert not (tmp_path / url.removeprefix("/uploads/")).exists()


async def test_delete_refuses_outside_root(tmp_path):
    outside = tmp_path.parent / "secret.txt"
    outside.write_text("x")
    with pytest.raises(ValueError):
        await ss.get_storage().delete("/uploads/../secret.txt")
    assert outside.exists()


async def test_upload_endpoint_requires_auth(client):
    r = await client.post("/api/uploads/image", files={"file": ("a.png", _img("PNG"), "image/png")})
    assert r.status_code == 401


async def test_upload_endpoint_ok_and_errors(client, tmp_path):
    await client.post("/api/auth/register", json=REG)
    r = await client.post("/api/uploads/image", files={"file": ("../../evil.png", _img("PNG"), "image/png")})
    assert r.status_code == 200 and r.json()["url"].startswith("/uploads/products/")
    r = await client.post("/api/uploads/image", data={"prefix": "logos"},
                          files={"file": ("a.png", _img("PNG"), "image/png")})
    assert r.json()["url"].startswith("/uploads/logos/")
    r = await client.post("/api/uploads/image", data={"prefix": "../x"},
                          files={"file": ("a.png", _img("PNG"), "image/png")})
    assert r.status_code == 422
    r = await client.post("/api/uploads/image", files={"file": ("x.jpg", b"hello", "image/jpeg")})
    assert r.status_code == 422 and r.json()["detail"] == {"code": "bad_type", "message_key": "errors.bad_type"}
    r = await client.post("/api/uploads/image", files={"file": ("x.jpg", b"\xff\xd8\xff" + b"0" * 8_500_000, "image/jpeg")})
    assert r.status_code == 422 and r.json()["detail"]["code"] == "too_large"


async def test_generated_pdfs_not_served_but_photos_are(client):
    import shutil
    from app.main import UPLOADS
    made = []
    try:
        for rel in ("quotes/zz-test/x.pdf", "reports/zz-test/x.pdf", "documents/zz-test/x.pdf", "products/zz-test/x.webp"):
            f = UPLOADS / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(b"data")
            made.append(f.parent)
        for url in ("/uploads/quotes/zz-test/x.pdf", "/uploads/reports/zz-test/x.pdf",
                    "/uploads/./quotes/zz-test/x.pdf", "/uploads/products/../quotes/zz-test/x.pdf",
                    "/uploads/QUOTES/zz-test/x.pdf", "/uploads/quotes./zz-test/x.pdf",
                    "/uploads/quotes%20/zz-test/x.pdf", "/uploads/quotes::$INDEX_ALLOCATION/zz-test/x.pdf",
                    "/uploads/documents/zz-test/x.pdf"):
            assert (await client.get(url)).status_code == 404, url
        assert (await client.get("/uploads/products/zz-test/x.webp")).status_code == 200
    finally:
        for d in made:
            shutil.rmtree(d, ignore_errors=True)



PDF = b"%PDF-1.4 1 0 obj<<>>endobj trailer<<>> %%EOF"


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "blue").save(out, "JPEG")
    return out.getvalue()


async def _upload_doc(c, data: bytes, name="doc.bin"):
    return await c.post("/api/uploads/document", files={"file": (name, data, "application/octet-stream")})


async def test_document_upload_pdf_and_image(producer, tmp_path):
    ss.set_root(tmp_path)
    try:
        p = await producer("Ali")
        r = await _upload_doc(p["client"], PDF, "cert.pdf")
        assert r.status_code == 200 and r.json()["url"].startswith(f"/uploads/documents/{p['user']['id']}/")
        assert r.json()["url"].endswith(".pdf")
        r = await _upload_doc(p["client"], _jpeg(), "plate.jpg")
        assert r.status_code == 200 and r.json()["url"].endswith(".webp")
    finally:
        ss.set_root(None)


async def test_document_upload_rejects_other(producer, tmp_path):
    ss.set_root(tmp_path)
    try:
        p = await producer("Ali")
        for data in (b"PK word document", b"random bytes", b"%PDF-" + b"0" * (8 * 1024 * 1024)):
            r = await _upload_doc(p["client"], data)
            assert r.status_code == 422, data[:10]
        codes = [(await _upload_doc(p["client"], d)).json()["detail"]["code"]
                 for d in (b"PK", b"%PDF-" + b"0" * (8 * 1024 * 1024))]
        assert codes == ["bad_document", "too_large"]
        assert not (tmp_path / "documents").exists()
    finally:
        ss.set_root(None)
