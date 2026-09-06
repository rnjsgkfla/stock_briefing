from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.app_env,
        "ai_provider": settings.ai_provider,
        "news_provider": settings.news_provider,
        "market_data_provider": settings.market_data_provider,
    }
