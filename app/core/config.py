from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Stock Briefing API"
    app_env: str = "local"
    database_url: str = "sqlite+aiosqlite:///./stock_briefing.db"
    redis_url: str = "redis://localhost:6379/0"

    ai_provider: Literal["mock", "gemini"] = "mock"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-3.7-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()
