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

    news_provider: Literal["mock", "alpha_vantage"] = "mock"
    alpha_vantage_api_key: SecretStr | None = None

    market_data_provider: Literal["mock", "toss"] = "mock"
    toss_invest_base_url: str = "https://openapi.tossinvest.com"
    toss_invest_client_id: SecretStr | None = None
    toss_invest_client_secret: SecretStr | None = None
    toss_invest_account: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
