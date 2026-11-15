from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.company import CompanyIn


class ProductIn(BaseModel):
    name_tr: str = Field(min_length=1, max_length=200)
    description_tr: str = Field(default="", max_length=4000)
    material_or_ingredients: str = Field(default="", max_length=1000)
    unit: Literal["kg", "adet", "metre", "koli"]
    moq: float = Field(gt=0)
    unit_weight_kg: float | None = Field(default=None, gt=0)
    price_floor: float = Field(gt=0)  # private: owner only, never in buyer/LLM output
    price_floor_currency: Literal["EUR", "USD"] = "EUR"
    photos: list[str] = Field(default_factory=list, max_length=6)


class MarketIn(BaseModel):
    country_code: Literal["DE"]


class OnboardingIn(BaseModel):
    company: CompanyIn
    product: ProductIn
    market: MarketIn

    @field_validator("product")
    @classmethod
    def _photo(cls, v: ProductIn) -> ProductIn:
        if not v.photos:
            raise ValueError("photo_required")
        return v
