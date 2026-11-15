import io

import pytest
from pypdf import PdfReader

from app.services import storage_service as ss
from tests.test_compliance_report import check, fails, kb, selector  # noqa: F401


@pytest.fixture(autouse=True)
def _tmp_root(tmp_path):
    ss.set_root(tmp_path)
    yield
    ss.set_root(None)


def text(data: bytes) -> str:
    return " ".join(p.extract_text() for p in PdfReader(io.BytesIO(data)).pages)


async def pdf(p, rep, lang=None):
    if lang:
        await p["client"].patch("/api/auth/me", json={"ui_language": lang})
    r = await p["client"].get(f"/api/compliance/reports/{rep['id']}/pdf")
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    return r, text(r.content).replace("​", "")


async def test_readiness_pdf_turkish_glyphs(producer, kb, fake_llm, db):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    r, t = await pdf(p, rep)
    assert 'filename="ihracat-hazirlik-raporu.pdf"' in r.headers["content-disposition"]
    for s in ("Türkiye tarafı", "ğ", "ş", "İ", "ı", "İhracat Hazırlık Raporu", "Bozkurt Gıda",
              "Kesin GTİP (12 hane) için gümrük müşavirinize danışın.", "Demo verisi",
              "Bu rapor bilgilendirme amaçlıdır; resmi mevzuat ve gümrük müşaviri görüşü esastır."):
        assert s in t, s
    flat = t.replace("\n", "").replace(" ", "")
    for i in rep["checklist"]:
        assert i["source_url"] in flat
    assert "9.5" not in t and "price_floor" not in t
    assert (await db.readiness_reports.find_one({}))["pdf_url"].endswith(".pdf")


async def test_readiness_pdf_footer_en(producer, kb, fake_llm):
    fake_llm.responses = fails
    p = await producer("Ali")
    rep = await check(p)
    r, t = await pdf(p, rep, "en")
    assert "export-readiness-report.pdf" in r.headers["content-disposition"]
    for s in ("Export Readiness Report", "Turkish side", "Demo data", "Check the final 12-digit GTİP",
              "This report is for information only; official regulations and a customs broker's advice take precedence."):
        assert s in t, s


async def test_pdf_ownership_and_no_match(producer, kb, fake_llm, db):
    fake_llm.responses = selector()
    p = await producer("Ali")
    await db.markets.update_many({}, {"$set": {"country_code": "FR"}})
    rep = await check(p)
    _, t = await pdf(p, rep)
    assert "Ticaret Müşavirliği" in t
    other = await producer("Veli")
    assert (await other["client"].get(f"/api/compliance/reports/{rep['id']}/pdf")).status_code == 404



async def test_pdf_ai_label_only_when_it_adds_text(producer, kb, fake_llm):
    p = await producer("Ali")
    fake_llm.responses = fails
    _, t = await pdf(p, await check(p))
    assert "Yapay zekâ açıklaması" not in t and "Neden uygun?" in t
    fake_llm.responses = selector()
    _, t = await pdf(p, await check(p), "en")
    assert "AI explanation" in t and "Why eligible?" in t
