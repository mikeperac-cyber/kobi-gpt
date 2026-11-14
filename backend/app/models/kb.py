from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints, field_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
OptText = Annotated[str, StringConstraints(strip_whitespace=True)]
Sector = Literal["tekstil", "gida", "otomotiv_yan_sanayi", "diger"]


def _http(v: str) -> str:
    if not v.startswith(("http://", "https://")):
        raise ValueError("source_url must be http(s)")
    return v


class _KB(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuleIn(_KB):
    id: Annotated[str, StringConstraints(pattern=r"^R\d+$")]
    title_tr: Text
    title_en: Text
    summary_tr: Text
    summary_en: Text
    what_to_do_tr: OptText = ""
    what_to_do_en: OptText = ""
    documents_tr: list[Text] = []
    documents_en: list[Text] = []
    country: Annotated[str, StringConstraints(pattern=r"^[A-Z]{2}$")] | None = None
    hs_prefixes: list[Text] = []
    sectors: list[Sector] = []
    channel: Literal["b2b", "b2c"] | None = None
    structural_use: bool | None = None
    side: Literal["TR", "DEST"]
    level: Literal["zorunlu", "koşullu", "önerilen"]
    source_url: Text

    _u = field_validator("source_url")(_http)


class IncentiveIn(_KB):
    id: Annotated[str, StringConstraints(pattern=r"^I\d+$")]
    name_tr: Text
    name_en: Text
    summary_tr: Text
    summary_en: Text
    what_to_do_tr: OptText = ""
    what_to_do_en: OptText = ""
    provider: Literal["Ticaret Bakanlığı", "KOSGEB", "Türk Eximbank", "TİM"]
    stages: list[Literal["ilk_ihracat", "sertifika", "fuar", "e_ihracat", "finansman"]] = []
    sectors: list[Sector] = []
    source_url: Text

    _u = field_validator("source_url")(_http)


class HsCodeIn(_KB):
    id: Annotated[str, StringConstraints(pattern=r"^\d{4}\.\d{2}$")]
    sector: Sector
    description_tr: Text
    description_en: Text
    note_tr: OptText = ""
    note_en: OptText = ""


KINDS = {
    "rules": ("kb_rules", RuleIn),
    "incentives": ("kb_incentives", IncentiveIn),
    "hs_codes": ("kb_hs_codes", HsCodeIn),
}
