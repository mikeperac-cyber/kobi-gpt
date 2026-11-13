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


def test_backend_error_codes_translated():
    import re
    app = Path(__file__).resolve().parents[1] / "app"
    src = {p: p.read_text(encoding="utf-8") for p in app.rglob("*.py")}
    codes = {"validation_error"}
    for text in src.values():
        codes |= set(re.findall(r'"errors\.(\w+)"', text))
    codes |= set(re.findall(r'"(\w+)"', re.search(r"KNOWN_CODES = \{(.*?)\}", src[app / "main.py"]).group(1)))
    codes |= set(re.findall(r'ValueError\("(\w+)"', src[app / "services" / "storage_service.py"]))
    for lang in ("tr", "en"):
        have = set(load(lang)["errors"])
        assert codes <= have, (lang, codes - have)
