from fastapi import APIRouter, HTTPException, status

from app.schemas.news import NewsAnalysisRequest, NewsAnalysisResult
from app.services.news_analysis import analyze_public_news

router = APIRouter()


@router.post("/analyze", response_model=NewsAnalysisResult)
async def analyze_news(payload: NewsAnalysisRequest) -> NewsAnalysisResult:
    try:
        return await analyze_public_news(payload)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
