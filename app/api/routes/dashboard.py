from fastapi import APIRouter

from app.schemas.dashboard import DashboardSnapshot
from app.services.market_data import get_dashboard_snapshot

router = APIRouter()


@router.get("", response_model=DashboardSnapshot)
async def get_dashboard() -> DashboardSnapshot:
    return get_dashboard_snapshot()
