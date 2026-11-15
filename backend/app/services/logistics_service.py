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
              "formula": f"{unit_weight_kg:g} kg × {quantity:g} × (1 + {pct:g}) = {gross:.2f} kg"}]
    bands, ftl, cur = rates["ltl_bands"]["bands"], rates["ftl"], rates["courier"]
    trucks = None
    if mode == "auto":
        mode = "ltl" if gross <= bands[-1]["max_kg"] else "ftl"
    if mode == "ltl":
        band = next((b for b in bands if gross <= b["max_kg"]), None)
        if band is None:
            raise ValueError("ltl_too_heavy")
        freight = round(gross * band["eur_per_kg"], 2)
        f = f"{gross:.2f} kg × {band['eur_per_kg']:g} EUR/kg (≤ {band['max_kg']:g} kg) = {freight:.2f} EUR"
    elif mode == "ftl":
        trucks = math.ceil(gross / ftl["truck_capacity_kg"])
        freight = round(trucks * ftl["eur_per_truck"], 2)
        f = (f"ceil({gross:.2f} / {ftl['truck_capacity_kg']:g}) = {trucks} × {ftl['eur_per_truck']:g} EUR"
             f" = {freight:.2f} EUR")
    elif mode == "courier":
        freight = round(max(cur["min_eur"], gross * cur["eur_per_kg"]), 2)
        f = f"max({cur['min_eur']:g}, {gross:.2f} kg × {cur['eur_per_kg']:g} EUR/kg) = {freight:.2f} EUR"
    else:
        raise ValueError("bad_mode")
    lines.append({"label_key": f"logistics.lines.{mode}", "value": freight, "formula": f})
    return Estimate(round(gross, 2), mode, trucks, freight, lines)
