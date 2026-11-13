import re
from pathlib import Path

from app.models.company import CERTS
from app.models.provinces import TR_PROVINCES

DATA = Path(__file__).resolve().parents[2] / "frontend" / "src" / "data"


def ts_list(name: str, const: str) -> list[str]:
    body = re.search(rf"export const {const}\b[^=]*=\s*\[(.*?)\]", (DATA / name).read_text(encoding="utf-8"), re.S).group(1)
    return re.findall(r"'([^']+)'", body)


def test_provinces_match_backend():
    assert ts_list("provinces.ts", "PROVINCES") == TR_PROVINCES


def test_certifications_match_backend():
    assert ts_list("certifications.ts", "CERTS") == CERTS
