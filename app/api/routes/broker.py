from fastapi import APIRouter, HTTPException, status

from app.core.config import get_settings
from app.schemas.broker import BrokerAccountList, BrokerPortfolio
from app.services.broker import get_broker_accounts, get_broker_portfolio

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


@router.get("/holdings", response_model=BrokerPortfolio)
async def get_holdings(account_seq: str | None = None) -> BrokerPortfolio:
    try:
        return await get_broker_portfolio(account_seq)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
