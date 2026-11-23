from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"  # repo root


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "kobigpt"
    jwt_secret: str = "dev-secret-change-me"
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-5-5"
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""
    llm_timeout_seconds: float = 45
    demo_llm_timeout_seconds: float = 25
    frontend_origin: str = "http://localhost:5173"
    email_provider: str = ""
    seed_password: str = ""
    demo_whatsapp_phone: str = ""  # presenter's own phone; seeded demo numbers are invented
    admin_email: str = ""

    @field_validator("jwt_secret")
    @classmethod
    def _empty_secret(cls, v: str) -> str:  # .env.example leaves it empty: local dev falls back to the dev default
        return v or "dev-secret-change-me"

    @property
    def llm_key(self) -> str | None:
        return getattr(self, f"{self.llm_provider}_api_key", "") or None


@lru_cache
def get_settings() -> Settings:
    return Settings()
