from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.db.session import get_db_session
from app.schemas.news import NewsAnalysisRequest, NewsAnalysisResult
from app.schemas.news_feed import NewsArticleResponse, NewsRefreshResult
from app.services.news_analysis import analyze_public_news
from app.services.news_feed import refresh_news_feed

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("/latest", response_model=list[NewsArticleResponse])
async def latest_news(
    session: DatabaseSession,
    limit: Annotated[int, Query(ge=1, le=50)] = 10,
) -> list[NewsArticle]:
    active_provider = get_settings().news_provider
    result = await session.scalars(
        select(NewsArticle)
        .where(NewsArticle.provider == active_provider)
        .order_by(NewsArticle.published_at.desc(), NewsArticle.id.desc())
        .limit(limit)
    )
    return list(result)


@router.post("/refresh", response_model=NewsRefreshResult)
async def refresh_news(session: DatabaseSession) -> NewsRefreshResult:
    try:
        return await refresh_news_feed(session)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@router.post("/analyze", response_model=NewsAnalysisResult)
async def analyze_news(payload: NewsAnalysisRequest) -> NewsAnalysisResult:
    try:
        return await analyze_public_news(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
