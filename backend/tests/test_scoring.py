from app.services.scoring import LEVEL_WEIGHTS, readiness_score


def it(level, applies=True, done=False):
    return {"level": level, "applies": applies, "done": done}


def test_readiness_weights():
    assert LEVEL_WEIGHTS == {"zorunlu": 3, "koşullu": 2, "önerilen": 1}
    assert readiness_score([it("zorunlu", done=True), it("koşullu"), it("önerilen", done=True)]) == 67


def test_nothing_applies_is_zero():
    assert readiness_score([]) == 0
    assert readiness_score([it("zorunlu", applies=False, done=True)]) == 0


def test_not_applicable_ignored():
    assert readiness_score([it("zorunlu", done=True), it("koşullu", applies=False)]) == 100


def test_round_half_up():
    # 5/8 = 62.5 -> 63 (banker's rounding would give 62)
    items = [it("zorunlu", done=True), it("koşullu", done=True), it("zorunlu", done=False)]
    assert readiness_score(items) == 63  # 5/8


# ---- lead_score (Task 25)
from app.services.scoring import lead_score, product_keywords  # noqa: E402

P = [{"name_tr": "İç Antep Fıstığı", "material_or_ingredients": "fıstık"}]


def _lead(**o):
    return {"source": "demo", "country": "FR", "email": "", "notes": "", "website": None, "company_name": "X", **o}


def test_score_components():
    assert lead_score(_lead(), P, "DE")["total"] == 0
    assert lead_score(_lead(source="rfq"), P, "DE")["breakdown"] == {"source": 40, "product_match": 0, "country": 0, "email": 0}
    assert lead_score(_lead(source="csv_import"), P, "DE")["total"] == 20
    assert lead_score(_lead(source="manual"), P, "DE")["total"] == 15
    assert lead_score(_lead(country="DE"), P, "DE")["breakdown"]["country"] == 15
    assert lead_score(_lead(email="a@b.de"), P, "DE")["breakdown"]["email"] == 15
    assert lead_score(_lead(notes="pistazien pistachio fistik"), P, "DE", "gida")["breakdown"]["product_match"] == 30
    many = "pistazien pistachio fistik antep nuss " * 2
    assert lead_score(_lead(notes=many), P, "DE", "gida")["breakdown"]["product_match"] == 30  # capped


def test_product_match_turkish_case():
    notes = "İÇ FISTIK Pistazien"  # "iç" is 2 chars -> dropped; "fistik" matches "fıstık" after folding
    assert "fistik" in product_keywords(P)
    assert lead_score(_lead(notes=notes), P, "DE")["breakdown"]["product_match"] == 10
    assert lead_score(_lead(notes=notes), P, "DE", "gida")["breakdown"]["product_match"] == 20  # + sector synonym
