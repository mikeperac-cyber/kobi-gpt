from pydantic import BaseModel, ConfigDict, Field


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
