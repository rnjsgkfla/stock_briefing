from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.bootstrap import DEMO_USER_ID
from app.db.models import Stock, WatchlistItem
from app.db.session import get_db_session
from app.schemas.watchlist import WatchlistCreate, WatchlistStock
from app.services.market_data import STOCK_CATALOG, get_mock_quote

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


def _to_response(item: WatchlistItem) -> WatchlistStock:
    price, change_percent, news_count = get_mock_quote(item.stock.symbol)
    return WatchlistStock(
        symbol=item.stock.symbol,
        name=item.stock.name,
        market=item.stock.market,
        currency=item.stock.currency,
        current_price=price,
        display_price=f"${price:,.2f}",
        change_percent=change_percent,
        news_count=news_count,
        added_at=item.created_at,
    )


@router.get("", response_model=list[WatchlistStock])
async def list_watchlist(
    session: DatabaseSession,
) -> list[WatchlistStock]:
    result = await session.scalars(
        select(WatchlistItem)
        .where(WatchlistItem.user_id == DEMO_USER_ID)
        .order_by(WatchlistItem.created_at, WatchlistItem.id)
    )
    return [_to_response(item) for item in result.unique().all()]


@router.post("", response_model=WatchlistStock, status_code=status.HTTP_201_CREATED)
async def add_watchlist_stock(
    payload: WatchlistCreate,
    session: DatabaseSession,
) -> WatchlistStock:
    metadata = STOCK_CATALOG.get(payload.symbol)
    if metadata is None:
        supported = ", ".join(sorted(STOCK_CATALOG))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"지원하지 않는 종목입니다. 현재 지원: {supported}",
        )

    stock = await session.scalar(select(Stock).where(Stock.symbol == payload.symbol))
    if stock is None:
        stock = Stock(symbol=payload.symbol, **metadata)
        session.add(stock)
        await session.flush()

    item = WatchlistItem(user_id=DEMO_USER_ID, stock_id=stock.id)
    session.add(item)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 관심 종목에 등록되어 있습니다.",
        ) from exc

    await session.refresh(item)
    item.stock = stock
    return _to_response(item)


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist_stock(
    symbol: str,
    session: DatabaseSession,
) -> Response:
    stock_id = await session.scalar(select(Stock.id).where(Stock.symbol == symbol.upper()))
    if stock_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="종목을 찾지 못했습니다.")

    result = await session.execute(
        delete(WatchlistItem).where(
            WatchlistItem.user_id == DEMO_USER_ID,
            WatchlistItem.stock_id == stock_id,
        )
    )
    if result.rowcount == 0:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="관심 종목이 아닙니다.")

    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
