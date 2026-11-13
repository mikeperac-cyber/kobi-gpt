from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.provinces import TR_PROVINCES

CERTS = ["ISO 9001", "ISO 22000", "BRC", "IFS", "OEKO-TEX", "Helal", "Organik", "CE", "IATF 16949", "Diğer"]


class ContactIn(BaseModel):
    phone: str = Field(min_length=3, max_length=40)
    email: str = Field(max_length=254)
    website: str | None = Field(default=None, max_length=300)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip()
        if "@" not in v.strip("@") or " " in v:
            raise ValueError("invalid email")
        return v


class CompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    city: str
    sector: Literal["tekstil", "gida", "otomotiv_yan_sanayi", "diger"]
    description_tr: str = Field(default="", max_length=4000)
    founded_year: int = Field(ge=1800, le=date.today().year)
    employee_count: int = Field(ge=1, le=100000)
    certifications: list[str] = Field(default_factory=list)
    contact: ContactIn
    logo_url: str | None = Field(default=None, max_length=500)
    min_order_note: str = Field(default="", max_length=500)

    @field_validator("city")
    @classmethod
    def _city(cls, v: str) -> str:
        if v not in TR_PROVINCES:
            raise ValueError("invalid_city")
        return v

    @field_validator("certifications")
    @classmethod
    def _certs(cls, v: list[str]) -> list[str]:
        if not set(v) <= set(CERTS):
            raise ValueError("invalid_certification")
        return list(dict.fromkeys(v))
