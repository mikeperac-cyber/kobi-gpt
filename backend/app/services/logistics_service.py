"""Deterministic, clearly estimated road-freight maths Turkey -> Germany. Pure: rates come in as a dict by key."""
import math
from dataclasses import asdict, dataclass, field

FREIGHT_INCOTERMS = {"CIF", "DAP"}


class NeedsWeight(Exception):
    pass


@dataclass
class Estimate:
    gross_kg: float
    mode: str
    trucks: int | None
    freight_eur: float
    lines: list = field(default_factory=list)
    estimated: bool = True

    def dict(self) -> dict:
        return asdict(self)


def freight_included(incoterm: str) -> bool:
    return incoterm in FREIGHT_INCOTERMS


def estimate(unit_weight_kg: float | None, quantity: float, rates: dict, mode: str = "auto") -> Estimate:
    if not quantity or quantity <= 0:
        raise ValueError("invalid_quantity")
    if not unit_weight_kg or unit_weight_kg <= 0:
        raise NeedsWeight()
    pct = rates["packaging_pct"]["value"]
    gross = round(unit_weight_kg * quantity * (1 + pct), 6)
    lines = [{"label_key": "logistics.lines.gross", "value": round(gross, 2),
              "formula": f"{unit_weight_kg:g} kg × {quantity:g} × (1 + {pct:g}) = {gross:.2f} kg",
              "values": {"unit": unit_weight_kg, "qty": quantity, "pct": pct, "gross": gross}}]
    bands, ftl, cur = rates["ltl_bands"]["bands"], rates["ftl"], rates["courier"]
    trucks = None
    if mode == "auto":
        mode = "ltl" if gross <= bands[-1]["max_kg"] else "ftl"
    if mode == "ltl":
        band = next((b for b in bands if gross <= b["max_kg"]), None)
        if band is None:
            raise ValueError("ltl_too_heavy")
        freight = round(gross * band["eur_per_kg"], 2)
        vals = {"gross": gross, "rate": band["eur_per_kg"], "max": band["max_kg"], "freight": freight}
        f = f"{gross:.2f} kg × {band['eur_per_kg']:g} EUR/kg (up to {band['max_kg']:g} kg) = {freight:.2f} EUR"
    elif mode == "ftl":
        trucks = math.ceil(gross / ftl["truck_capacity_kg"])
        freight = round(trucks * ftl["eur_per_truck"], 2)
        vals = {"gross": gross, "cap": ftl["truck_capacity_kg"], "trucks": trucks, "rate": ftl["eur_per_truck"],
                "freight": freight}
        f = (f"ceil({gross:.2f} / {ftl['truck_capacity_kg']:g}) = {trucks} × {ftl['eur_per_truck']:g} EUR"
             f" = {freight:.2f} EUR")
    elif mode == "courier":
        freight = round(max(cur["min_eur"], gross * cur["eur_per_kg"]), 2)
        vals = {"min": cur["min_eur"], "gross": gross, "rate": cur["eur_per_kg"], "freight": freight}
        f = f"max({cur['min_eur']:g}, {gross:.2f} kg × {cur['eur_per_kg']:g} EUR/kg) = {freight:.2f} EUR"
    else:
        raise ValueError("bad_mode")
    lines.append({"label_key": f"logistics.lines.{mode}", "value": freight, "formula": f, "values": vals})
    return Estimate(round(gross, 2), mode, trucks, freight, lines)


def render_formula(line: dict, template: str, lang: str) -> str:
    """Human formula with locale numbers (de/tr: 1.234,56; en: 1,234.56). Falls back to the stored English text."""
    vals = line.get("values")
    if not vals:
        return line["formula"]

    def n(k, v):
        s = f"{v:,.2f}" if k in ("gross", "freight") else f"{v:,.2f}".rstrip("0").rstrip(".")
        return s if lang == "en" else s.replace(",", "X").replace(".", ",").replace("X", ".")
    return template.format(**{k: n(k, v) for k, v in vals.items()})
