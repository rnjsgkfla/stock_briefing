from fastapi import APIRouter

from app.api.routes import dashboard, health, news_analysis, watchlist

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(news_analysis.router, prefix="/news", tags=["news"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(watchlist.router, prefix="/watchlist", tags=["watchlist"])
