from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.dashboard import DashboardSnapshot
from app.services.morning_briefing import build_dashboard_snapshot

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


@router.get("", response_model=DashboardSnapshot)
async def get_dashboard(
    session: DatabaseSession,
    demo_portfolio: bool = False,
) -> DashboardSnapshot:
    return await build_dashboard_snapshot(session, demo_portfolio=demo_portfolio)
