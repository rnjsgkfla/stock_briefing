import asyncio
from typing import Any

from app.schemas.news import NewsAnalysisRequest
from app.services.news_analysis import analyze_public_news
from app.workers.celery_app import celery_app


@celery_app.task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def analyze_news_task(payload: dict[str, Any]) -> dict[str, Any]:
    request = NewsAnalysisRequest.model_validate(payload)
    result = asyncio.run(analyze_public_news(request))
    return result.model_dump(mode="json")


@celery_app.task
def create_morning_briefings() -> dict[str, str]:
    return {
        "status": "skipped",
        "reason": "시장·뉴스 수집기가 연결된 뒤 활성화됩니다.",
    }
