import pytest

from app.services.logistics_service import NeedsWeight, estimate, freight_included

RATES = {"packaging_pct": {"value": 0.0},
         "ltl_bands": {"bands": [{"max_kg": 500, "eur_per_kg": 0.6}, {"max_kg": 3000, "eur_per_kg": 0.35},
                                 {"max_kg": 12000, "eur_per_kg": 0.25}]},
         "ftl": {"eur_per_truck": 2500, "truck_capacity_kg": 24000},
         "courier": {"eur_per_kg": 8.0, "min_eur": 60}}


def test_gross_weight():
    r = {**RATES, "packaging_pct": {"value": 0.08}}
    e = estimate(2, 100, r)
    assert e.gross_kg == 216.0 and e.estimated and e.lines[0]["label_key"] == "logistics.lines.gross"


def test_ftl_trucks_ceil():
    e = estimate(1, 24001, RATES)
    assert (e.mode, e.trucks, e.freight_eur) == ("ftl", 2, 5000.0)
    assert estimate(1, 24000, RATES).trucks == 1


def test_ltl_band_edges():
    e = estimate(1, 500, RATES)
    assert e.mode == "ltl" and e.freight_eur == 300.0  # exactly 500 kg -> first band
    assert estimate(1, 501, RATES).freight_eur == 175.35
    assert estimate(1, 12000, RATES).mode == "ltl" and estimate(1, 12001, RATES).mode == "ftl"


def test_courier_min_charge():
    assert estimate(2, 1, RATES, "courier").freight_eur == 60.0
    assert estimate(10, 1, RATES, "courier").freight_eur == 80.0


def test_freight_only_cif_dap():
    assert [freight_included(i) for i in ("EXW", "FCA", "FOB", "CIF", "DAP")] == [False, False, False, True, True]


def test_estimate_edges():
    for q in (0, -1):
        with pytest.raises(ValueError):
            estimate(1, q, RATES)
    with pytest.raises(NeedsWeight):
        estimate(None, 10, RATES)
