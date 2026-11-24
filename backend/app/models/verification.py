from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class VerificationIn(BaseModel):
    kind: Literal["tax_plate", "certificate"]
    name: str = Field(default="", max_length=80)  # certificate name as written in the company profile
    issuer: str = Field(default="", max_length=120)
    valid_until: date | None = None
    file_url: str = Field(max_length=300)
