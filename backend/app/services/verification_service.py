from datetime import date, datetime

from app.core.text import tr_fold


def fold(name: str) -> str:
    """Certificate names compare case- and Turkish-letter-insensitively ("İSO 22000" == "iso 22000")."""
    return trfold(name).strip()


def _live(doc: dict, today: date) -> bool:
    return not doc.get("valid_until") or date.fromisoformat(doc["valid_until"]) >= today


async def public_trust(db, company: dict, today: date) -> dict:
    """What a buyer may see: which facts were checked and are still valid. Never files, reviewers or reasons.
    Certificates follow the company profile, so a removed certificate disappears and an expired one drops back
    to 'self-declared' without anyone acting."""
    docs = await db.verifications.find({"company_id": str(company["_id"]), "status": "verified"}).to_list(200)
    live = [d for d in docs if _live(d, today)]
    certs = {}
    for d in live:
        if d["kind"] == "certificate":
            certs[fold(d["name"])] = max(d.get("valid_until") or "", certs.get(fold(d["name"]), "")) or None
    plates = [d for d in live if d["kind"] == "tax_plate"]
    at = max((d["reviewed_at"] for d in plates if isinstance(d.get("reviewed_at"), datetime)), default=None)
    return {
        "company_verified": bool(plates),
        "verified_at": at.date().isoformat() if at else None,
        "certificates": [{"name": c, "verified": fold(c) in certs, "valid_until": certs.get(fold(c))}
                         for c in company.get("certifications") or []],
    }
