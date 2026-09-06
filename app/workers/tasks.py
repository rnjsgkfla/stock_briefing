import asyncio
from typing import Any

from app.db.session import async_session_factory
from app.schemas.news import NewsAnalysisRequest
from app.services.news_analysis import analyze_public_news
from app.services.news_feed import refresh_news_feed
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


@celery_app.task(
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=3,
)
def refresh_news_feed_task() -> dict[str, Any]:
    async def run() -> dict[str, Any]:
        async with async_session_factory() as session:
            result = await refresh_news_feed(session)
            return result.model_dump(mode="json")

    return asyncio.run(run())


@celery_app.task
def create_morning_briefings() -> dict[str, str]:
    return {
        "status": "skipped",
        "reason": "시장·뉴스 수집기가 연결된 뒤 활성화됩니다.",
    }
