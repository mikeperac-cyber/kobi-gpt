from typing import Literal

from pydantic import BaseModel, Field


class ProductDraftOut(BaseModel):
    """AI suggestion from product photos. No numeric fields on purpose: MOQ, weight and price are the producer's."""
    name_tr: str | None = Field(default=None, max_length=200)
    description_tr: str | None = Field(default=None, max_length=1500)
    material_or_ingredients: str | None = Field(default=None, max_length=500)
    unit: Literal["kg", "adet", "metre", "koli"] | None = None


class DraftIn(BaseModel):
    photos: list[str] = Field(min_length=1, max_length=6)
