from typing import Literal

from pydantic import BaseModel, Field

STATUSES = ["new", "draft_ready", "sent", "replied", "quoted", "won", "lost", "do_not_contact"]
PATCHABLE = {"new", "won", "lost", "do_not_contact"}  # the rest are set by the outreach flow


class LeadIn(BaseModel):
    company_name: str = Field(min_length=1, max_length=200)
    country: str = Field(pattern=r"^[A-Za-z]{2}$")
    contact_name: str = Field(default="", max_length=120)
    email: str = Field(default="", max_length=254)
    website: str | None = Field(default=None, max_length=300)
    notes: str = Field(default="", max_length=2000)
    source_note: str = Field(default="", max_length=200)


class Mapping(BaseModel):
    company_name: str
    country: str | None = None
    contact_name: str | None = None
    email: str | None = None
    website: str | None = None
    notes: str | None = None


class ImportIn(BaseModel):
    file_id: str
    mapping: Mapping
    source_note: str = Field(default="", max_length=200)


class StatusIn(BaseModel):
    status: str
    # required when status == "won": what the producer says the deal was worth (self-reported, never converted)
    deal_value: float | None = Field(default=None, gt=0, le=1_000_000_000, allow_inf_nan=False)
    deal_currency: Literal["EUR", "USD", "TRY"] | None = None
