"""Settings loaded from environment / .env. Keep env access here only."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Complaint Management System"
    environment: str = Field(default="development")

    # SQLite by default; point at Postgres for the compose setup.
    database_url: str = Field(default="sqlite:///./complaints.db")

    # Empty key => nodes use rule-based fallbacks instead of Groq.
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="openai/gpt-oss-120b")
    groq_fallback_model: str = Field(default="openai/gpt-oss-20b")
    llm_temperature: float = Field(default=0.2)

    frontend_origin: str = Field(default="http://localhost:5173")

    max_upload_bytes: int = Field(default=5 * 1024 * 1024)  # 5 MB
    allowed_upload_extensions: str = Field(
        default=".pdf,.txt,.eml,.md,.csv,.png,.jpg,.jpeg,.gif,.webp"
    )

    # false: return quickly and process in background (client polls).
    # true: wait for the agent in-request (handy for tests).
    sync_processing: bool = Field(default=False)

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key.strip())

    @property
    def allowed_extensions(self) -> set[str]:
        return {
            ext.strip().lower() if ext.strip().startswith(".") else f".{ext.strip().lower()}"
            for ext in self.allowed_upload_extensions.split(",")
            if ext.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
