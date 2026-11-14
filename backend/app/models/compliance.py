from typing import Literal

from pydantic import BaseModel, Field

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


class CheckIn(BaseModel):
    product_id: str
    channel: Literal["b2b", "b2c"] = "b2b"
    structural_use: bool = False


class TickIn(BaseModel):
    done: bool


class RuleExplainItem(BaseModel):
    rule_id: str
    applies: bool
    reason: str = ""
    next_step: str = ""


class RuleExplainOut(BaseModel):
    items: list[RuleExplainItem]


class IncentiveExplainItem(BaseModel):
    incentive_id: str
    applies: bool
    why: str = ""


class IncentiveExplainOut(BaseModel):
    items: list[IncentiveExplainItem]


class NextStep(BaseModel):
    rule_id: str
    text: str


class NextStepsOut(BaseModel):
    steps: list[NextStep] = Field(max_length=3)
