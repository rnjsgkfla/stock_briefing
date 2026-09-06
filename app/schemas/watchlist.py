from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class WatchlistCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=16)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, symbol: str) -> str:
        return symbol.strip().upper()


class WatchlistStock(BaseModel):
    symbol: str
    name: str
    market: str
    currency: str
    current_price: float
    display_price: str
    change_percent: float | None
    news_count: int
    added_at: datetime
    price_provider: str
