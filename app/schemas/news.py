from typing import Literal

from pydantic import BaseModel, Field, field_validator


class NewsAnalysisRequest(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    content: str = Field(min_length=20, max_length=30_000)
    source_url: str | None = Field(default=None, max_length=2_000)
    candidate_symbols: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("candidate_symbols")
    @classmethod
    def normalize_symbols(cls, symbols: list[str]) -> list[str]:
        return list(dict.fromkeys(symbol.strip().upper() for symbol in symbols if symbol.strip()))


class NewsAnalysisResult(BaseModel):
    summary: str = Field(description="기사의 핵심 사실을 담은 짧은 한국어 요약")
    related_symbols: list[str]
    impact_direction: Literal["positive", "neutral", "negative", "mixed"]
    importance: Literal["low", "medium", "high"]
    facts: list[str]
    interpretation: str
    uncertainties: list[str]
    provider: Literal["mock", "gemini"]


class NewsEnrichmentItem(BaseModel):
    index: int
    korean_summary: str = Field(min_length=20, max_length=800)
    category: Literal["금리", "환율", "반도체", "실적", "전쟁·지정학", "기업", "기타"]


class NewsEnrichmentBatch(BaseModel):
    items: list[NewsEnrichmentItem]
