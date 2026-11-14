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
