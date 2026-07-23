"""Application configuration.

Everything that changes between environments lives here and is read from
environment variables (or a local .env file). Nothing else in the codebase
should reach for os.environ directly.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core service settings.
    app_name: str = "AI Complaint Management System"
    environment: str = Field(default="development")

    # Database. Defaults to a local SQLite file so the project runs with zero
    # setup, but any SQLAlchemy URL works. For the production stack we point
    # this at Postgres (see docker-compose.yml and the README).
    database_url: str = Field(default="sqlite:///./complaints.db")

    # Groq / LLM settings. When no key is present the agent falls back to a
    # deterministic heuristic so the workflow still runs end to end.
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="gemma2-9b-it")
    groq_fallback_model: str = Field(default="llama-3.3-70b-versatile")
    llm_temperature: float = Field(default=0.2)

    # CORS. The Vite dev server runs on 5173 by default.
    frontend_origin: str = Field(default="http://localhost:5173")

    @property
    def has_groq(self) -> bool:
        return bool(self.groq_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so we only parse the environment once."""
    return Settings()
