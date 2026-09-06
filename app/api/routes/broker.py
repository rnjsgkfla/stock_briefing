from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.broker import BrokerAccountList
from app.services.broker import get_broker_accounts

router = APIRouter()


@router.get("/accounts", response_model=BrokerAccountList)
async def list_broker_accounts() -> BrokerAccountList:
    settings = get_settings()
    try:
        accounts = await get_broker_accounts()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    return BrokerAccountList(provider=settings.market_data_provider, accounts=accounts)
