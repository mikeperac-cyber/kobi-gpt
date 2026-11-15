"""Shared CSV helpers (KB admin import and lead import)."""
import csv
import io

MAX_IMPORT = 2 * 1024 * 1024
DANGER = ("=", "+", "-", "@", "\t", "\r")  # Excel treats these leading chars as formulas


def unguard(c: str) -> str:
    """Undo the export-side formula guard: a leading ' before a dangerous char is stripped."""
    return c[1:] if c.startswith("'") and c[1:].startswith(DANGER) else c


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        return raw.decode("cp1254", errors="replace")  # Excel's Turkish Windows codepage


def delimiter(text: str) -> str:
    header = text.split("\n", 1)[0]
    return ";" if header.count(";") > header.count(",") else ","


def parse_csv(data: bytes) -> tuple[list[str], list[dict]]:
    text = decode(data)
    rd = csv.DictReader(io.StringIO(text), delimiter=delimiter(text))
    headers = [h.strip() for h in (rd.fieldnames or []) if h]
    rows = [{k.strip(): unguard((v or "").strip()) for k, v in r.items() if k} for r in rd]
    return headers, rows
