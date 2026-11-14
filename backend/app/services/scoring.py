LEVEL_WEIGHTS = {"zorunlu": 3, "koşullu": 2, "önerilen": 1}


def readiness_score(items: list[dict]) -> int:
    """Weighted share of applicable checklist items that are done, 0-100 (half rounds up)."""
    applicable = [i for i in items if i["applies"]]
    total = sum(LEVEL_WEIGHTS[i["level"]] for i in applicable)
    if not total:
        return 0
    done = sum(LEVEL_WEIGHTS[i["level"]] for i in applicable if i["done"])
    return int(100 * done / total + 0.5)
