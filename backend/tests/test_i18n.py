import json
from pathlib import Path

I18N = Path(__file__).resolve().parents[2] / "frontend" / "src" / "i18n"


def load(lang):
    return json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))


def flat(d, p=""):
    out = {}
    for k, v in d.items():
        key = f"{p}.{k}" if p else k
        out.update(flat(v, key) if isinstance(v, dict) else {key: v})
    return out


def test_tr_en_key_parity():
    tr, en = load("tr"), load("en")
    assert set(flat(tr)) == set(flat(en)), set(flat(tr)) ^ set(flat(en))


def test_no_empty_strings():
    for lang in ("tr", "en"):
        assert all(isinstance(v, str) and v.strip() for v in flat(load(lang)).values())
