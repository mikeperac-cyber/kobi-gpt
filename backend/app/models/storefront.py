from typing import Literal

from pydantic import BaseModel, Field

INCOTERMS = ("EXW", "FCA", "FOB", "CIF", "DAP")
MissingStr = str | None  # None = no fact available; listed in SiteConfig.missing


class IntakeIn(BaseModel):
    text: str = Field(max_length=4000)
    positioning: Literal["b2b", "b2c"] = "b2b"
    lead_time: str | None = Field(default=None, max_length=200)
    sample_policy: str | None = Field(default=None, max_length=300)
    incoterms: list[Literal["EXW", "FCA", "FOB", "CIF", "DAP"]] = Field(default_factory=list)


class Hero(BaseModel):
    headline: MissingStr = None
    subheadline: MissingStr = None
    cta: MissingStr = None


class About(BaseModel):
    story: MissingStr = None
    city: MissingStr = None
    founded_year: int | None = None
    team_size: int | None = None
    certifications: list[str] = Field(default_factory=list)


class Spec(BaseModel):
    label: str
    value: str


class ProductBlock(BaseModel):
    product_id: str
    name: MissingStr = None
    short: MissingStr = None
    long: MissingStr = None
    specs: list[Spec] = Field(default_factory=list)
    moq: MissingStr = None
    packaging: MissingStr = None
    photos: list[str] = Field(default_factory=list)


class ExportInfo(BaseModel):
    incoterms: list[str] = Field(default_factory=list)
    lead_time: MissingStr = None
    sample_policy: MissingStr = None


class Rfq(BaseModel):
    title: MissingStr = None
    intro: MissingStr = None


class Footer(BaseModel):
    note: MissingStr = None


class Seo(BaseModel):
    title: MissingStr = None
    description: MissingStr = None


class LocalizedContent(BaseModel):
    hero: Hero = Field(default_factory=Hero)
    about: About = Field(default_factory=About)
    products: list[ProductBlock] = Field(default_factory=list)
    why_us: list[str] = Field(default_factory=list)  # 3-4 items
    export_info: ExportInfo = Field(default_factory=ExportInfo)
    rfq: Rfq = Field(default_factory=Rfq)
    footer: Footer = Field(default_factory=Footer)
    seo: Seo = Field(default_factory=Seo)


class SiteConfig(BaseModel):
    de: LocalizedContent
    en: LocalizedContent
    review: LocalizedContent
    review_language: Literal["tr", "en"]
    slug_suggestion: str
    template: Literal["industrial", "natural", "textile"]
    missing: list[str] = Field(default_factory=list)
    positioning: Literal["b2b", "b2c"]
