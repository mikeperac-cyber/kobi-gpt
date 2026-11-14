"""PDF rendering (reportlab). Takes already-public dicts only: never a product document (price_floor stays out)."""
import io
import json
from datetime import date, datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate, Paragraph, Spacer

BRAND = colors.HexColor("#C8102E")
_APP = Path(__file__).resolve().parents[1]
STRINGS = json.loads((_APP / "pdf_strings.json").read_text(encoding="utf-8"))
_registered = False


def register_fonts() -> None:
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont("NotoSans", str(_APP / "assets/fonts/NotoSans-Regular.ttf")))
    pdfmetrics.registerFont(TTFont("NotoSans-Bold", str(_APP / "assets/fonts/NotoSans-Bold.ttf")))
    pdfmetrics.registerFontFamily("NotoSans", normal="NotoSans", bold="NotoSans-Bold")
    _registered = True


def _style(name, font="NotoSans", size=9.5, **kw):
    return ParagraphStyle(name, fontName=font, fontSize=size, leading=size * 1.35, **kw)


def _fmt_date(v, lang: str, months: list[str]) -> str:
    if isinstance(v, str):
        try:
            v = datetime.fromisoformat(v)
        except ValueError:
            return v
    if not isinstance(v, (date, datetime)):
        return ""
    return f"{v.day:02d}.{v.month:02d}.{v.year}" if lang == "tr" else f"{v.day} {months[v.month]} {v.year}"


def _p(text, style) -> Paragraph:
    return Paragraph(escape(str(text or "")), style)


def _url(u: str, style, label: str) -> Paragraph:
    shown = escape(u).replace("/", "/​")  # break points so long URLs wrap inside the page
    return Paragraph(f'{label}: <a href="{escape(u)}" color="#1a55b3">{shown}</a>', style)


def readiness_pdf(report: dict, company_public: dict, lang: str) -> bytes:
    register_fonts()
    t = STRINGS[lang if lang in STRINGS else "tr"]
    h1 = _style("h1", "NotoSans-Bold", 18, textColor=BRAND)
    h2 = _style("h2", "NotoSans-Bold", 12, textColor=BRAND, spaceBefore=10, spaceAfter=4)
    h3 = _style("h3", "NotoSans-Bold", 10.5, spaceBefore=6)
    b, bold = _style("b"), _style("bold", "NotoSans-Bold")
    title_st = _style("it", "NotoSans-Bold", leftIndent=8, spaceBefore=6)
    small = _style("small", size=8.5, textColor=colors.HexColor("#444444"), leftIndent=8)
    body = _style("body", leftIndent=8, spaceBefore=3)
    d = lambda v: _fmt_date(v, lang, t["months"])  # noqa: E731
    contact = company_public.get("contact") or {}
    city = f', {company_public["city"]}' if company_public.get("city") else ""
    story = [_p(t["title"], h1), Spacer(1, 4), _p(f'{t["company"]}: {company_public.get("name", "")}{city}', bold),
             _p(" · ".join(str(contact[k]) for k in ("email", "phone", "website") if contact.get(k)), small),
             _p(f'{t["date"]}: {d(report.get("created_at") or datetime.now())}', b),
             _p(f'{t["product"]}: {report.get("product_name", "")} · {t["country"]}: {report.get("country", "")}', b),
             _p(f'{t["gtip"]}: {report.get("hs6", "")}', bold), _p(t["gtip_warning"], b), _p(t["checklist"], h2)]
    for side in ("TR", "DEST"):
        rows = [i for i in report.get("checklist", []) if i["side"] == side]
        if rows:
            story.append(_p(t[side], h3))
        for i in rows:
            na = "" if i.get("applies", True) else " — " + t["not_applicable"]
            story += [_p(f'{i[f"title_{lang}"]} — {t[i["level"]]}{na}', title_st), _p(i.get("summary"), body)]
            if i.get("reason"):
                story.append(_p(f'{t["ai"]}: {i["reason"]}', small))
            story += [_url(i["source_url"], small, t["source"]),
                      _p(t["verified"].format(d=d(i["last_verified"])) if i.get("last_verified") else t["unverified"], small),
                      _p(t["done"] if i.get("done") else t["todo"], small)]
    if report.get("no_match"):
        story += [Spacer(1, 6), _p(t["no_match"], bold)] + [_p("• " + e, b) for e in t["experts"]]
    if report.get("incentives"):
        story.append(_p(t["incentives"], h2))
        for i in report["incentives"]:
            story += [_p(f'{i[f"name_{lang}"]} ({i.get("provider", "")})', title_st),
                      _p(f'{t["why"]} {i.get("why", "")}', small), _url(i["source_url"], small, t["source"])]
    story += [_p(t["score"], h2), _p(f'{report.get("score", 0)} / 100', bold), _p(t["formula"], small)]
    if report.get("next_steps"):
        story.append(_p(t["next_steps"], h2))
        story += [_p(f'{n}. {s["text"]}', b) for n, s in enumerate(report["next_steps"][:3], 1)]

    def page(canvas, doc):
        canvas.saveState()
        canvas.setFillColor(BRAND)
        canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor("#555555"))
        canvas.setFont("NotoSans", 7.5)
        canvas.drawString(18 * mm, 10 * mm, t["footer"])
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, t["page"].format(n=doc.page))
        canvas.restoreState()

    buf = io.BytesIO()
    doc = BaseDocTemplate(buf, pagesize=A4, title=t["title"], author="KOBİ-GPT")
    doc.addPageTemplates(PageTemplate(id="p", onPage=page, frames=[
        Frame(18 * mm, 16 * mm, A4[0] - 36 * mm, A4[1] - 34 * mm, id="f")]))
    doc.build(story)
    return buf.getvalue()
