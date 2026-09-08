from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class NewsArticleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    summary: str
    korean_summary: str | None
    category: str
    content_source: str
    extraction_status: str
    extracted_at: datetime | None
    source: str
    source_url: str
    published_at: datetime
    symbols: list[str]
    sentiment: str | None
    provider: str


class NewsRefreshResult(BaseModel):
    provider: Literal["mock", "alpha_vantage"]
    collected_count: int
    stored_count: int
    duplicate_count: int
    extracted_count: int = 0
    summarized_count: int = 0
