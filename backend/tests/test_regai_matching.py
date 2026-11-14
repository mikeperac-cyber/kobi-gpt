import json
from pathlib import Path

import pytest

from app.services.regai_service import filter_incentives, match_rules

DATA = Path(__file__).resolve().parents[1] / "app" / "seed" / "data"
RULES = json.loads((DATA / "kb_rules.json").read_text(encoding="utf-8"))
INCENTIVES = json.loads((DATA / "kb_incentives.json").read_text(encoding="utf-8"))
HS = json.loads((DATA / "kb_hs_codes.json").read_text(encoding="utf-8"))


def ids(**kw):
    kw.setdefault("country", "DE")
    kw.setdefault("structural_use", False)
    return {r["id"] for r in match_rules(RULES, **kw)}


def test_pistachio_b2b():
    got = ids(hs6="2008.19", sector="gida", channel="b2b")
    assert {"R1", "R3", "R7", "R8"} <= got
    assert not {"R9", "R10"} & got


def test_pistachio_b2c():
    assert {"R1", "R3", "R7", "R8", "R9", "R10"} <= ids(hs6="2008.19", sector="gida", channel="b2c")


def test_towels():
    assert {"R1", "R2", "R4", "R5", "R6"} <= ids(hs6="6302.60", sector="tekstil", channel="b2b")


def test_bolts():
    base = dict(hs6="7318.15", sector="otomotiv_yan_sanayi", channel="b2b")
    got = ids(**base)
    assert {"R1", "R2", "R12", "R13"} <= got and "R15" not in got
    assert "R15" in ids(**base, structural_use=True)


def test_r11_and_r14_sector_rules():
    assert "R11" in ids(hs6="6302.60", sector="tekstil", channel="b2c")
    assert "R11" not in ids(hs6="6302.60", sector="tekstil", channel="b2b")
    assert "R14" in ids(hs6="7318.15", sector="otomotiv_yan_sanayi", channel="b2b")
    assert "R14" not in ids(hs6="2008.19", sector="gida", channel="b2b")
    # R13 needs both hs 7318 and the automotive sector
    assert "R13" not in ids(hs6="7318.15", sector="diger", channel="b2b")
    assert "R13" not in ids(hs6="2008.19", sector="otomotiv_yan_sanayi", channel="b2b")


def test_unknown_country_only_turkish_side():
    assert ids(country="US", hs6="2008.19", sector="gida", channel="b2c") == {"R1"}


def test_sorted_numerically():
    out = [r["id"] for r in match_rules(RULES, country="DE", hs6="7318.15",
           sector="otomotiv_yan_sanayi", channel="b2c", structural_use=True)]
    assert out == sorted(out, key=lambda i: int(i[1:]))
    assert out.index("R2") < out.index("R10")


def test_every_rule_reachable():
    reached = set()
    for h in HS:
        for ch in ("b2b", "b2c"):
            for su in (False, True):
                for sector in ("tekstil", "gida", "otomotiv_yan_sanayi", "diger", h["sector"]):
                    reached |= ids(hs6=h["id"], sector=sector, channel=ch, structural_use=su)
    assert {r["id"] for r in RULES} <= reached


def test_filter_incentives():
    assert "I5" in {i["id"] for i in filter_incentives(INCENTIVES, "tekstil")}
    assert "I5" not in {i["id"] for i in filter_incentives(INCENTIVES, "gida")}
    assert len(filter_incentives(INCENTIVES, "gida")) == len(INCENTIVES) - 1
