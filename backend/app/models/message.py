from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DraftIn(BaseModel):
    tone: list[str] = Field(default_factory=list, max_length=3)


class MessageEditIn(BaseModel):
    model_config = ConfigDict(extra="forbid")  # status / approval fields can never be set here
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=300)


class DraftOut(BaseModel):
    subject: str
    body: str


class TranslationOut(BaseModel):
    text: str


class ReplyIn(BaseModel):
    text: str = Field(min_length=1, max_length=10000)

    @field_validator("text")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("blank")
        return v


INCOTERMS = {"EXW", "FCA", "FOB", "CIF", "DAP", "other"}


class ReplyTerms(BaseModel):
    quantity: str | None = None
    incoterm: str | None = None
    delivery_date: str | None = None
    certifications: list[str] = Field(default_factory=list)

    @field_validator("incoterm", mode="before")
    @classmethod
    def _incoterm(cls, v):
        if not isinstance(v, str) or not v.strip():
            return None
        v = v.strip()
        return v.upper() if v.upper() in INCOTERMS else "other"


class ReplyAnalysisOut(BaseModel):
    translation: str | None = None
    summary: list[str] = Field(min_length=3, max_length=3)  # never truncate/pad: invalid -> retry/fallback
    intent: Literal["interested", "asks_price", "asks_samples", "not_interested", "other"]
    terms: ReplyTerms = Field(default_factory=ReplyTerms)
    red_flags: list[str] = Field(default_factory=list)
    suggested_reply: DraftOut
    opt_out: bool = False
