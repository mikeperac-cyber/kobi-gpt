import unicodedata

_TR = str.maketrans("şŞğĞıIİöÖüÜçÇ", "ssggiiioouucc")


def tr_fold(s: str) -> str:
    """Turkish-aware fold: map special letters before lowercasing (Python's "İ".lower() is i + combining dot)."""
    s = unicodedata.normalize("NFKD", s.translate(_TR).lower())
    return "".join(c for c in s if not unicodedata.combining(c))
