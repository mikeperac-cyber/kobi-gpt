from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

INCOTERMS = ("EXW", "FCA", "FOB", "CIF", "DAP")
PAYMENT_TERMS = ("cash_advance", "advance_30_70", "lc", "cad")


class QuoteIn(BaseModel):
    lead_id: str
    product_id: str
    quantity: float  # > 0 is checked in the service so the code is `invalid_quantity`
    unit_price: float
    currency: Literal["EUR", "USD"]
    incoterm: Literal["EXW", "FCA", "FOB", "CIF", "DAP"]
    payment_terms: Literal["cash_advance", "advance_30_70", "lc", "cad"]
    valid_until: date
    unit_weight_kg: float | None = Field(default=None, gt=0)


class SampleTaskIn(BaseModel):
    product_id: str
    sample_weight_kg: float = Field(default=2.0, gt=0, le=30)


class Band(BaseModel):
    max_kg: float = Field(gt=0)
    eur_per_kg: float = Field(gt=0)


class RatesIn(BaseModel):
    packaging_pct: float = Field(ge=0, le=1)
    ltl_bands: list[Band] = Field(min_length=1)
    ftl_eur_per_truck: float = Field(gt=0)
    ftl_truck_capacity_kg: float = Field(gt=0)
    courier_eur_per_kg: float = Field(gt=0)
    courier_min_eur: float = Field(gt=0)

    @model_validator(mode="after")
    def _ascending(self):
        m = [b.max_kg for b in self.ltl_bands]
        if any(a >= b for a, b in zip(m, m[1:])):
            raise ValueError("bands must be ascending")
        return self
