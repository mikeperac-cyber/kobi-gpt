from typing import Literal

from pydantic import BaseModel

Confidence = Literal["yüksek", "orta", "düşük"]


class GtipLLMCandidate(BaseModel):
    code: str
    description: str
    confidence: Confidence
    reasoning: str


class GtipOut(BaseModel):
    candidates: list[GtipLLMCandidate]  # capped to 3 in code, not rejected


class GtipCandidate(GtipLLMCandidate):
    in_kb: bool


class GtipIn(BaseModel):
    product_id: str
    processing: Literal["roasted", "raw", "na"] | None = None


class GtipConfirmIn(BaseModel):
    product_id: str
    code: str
