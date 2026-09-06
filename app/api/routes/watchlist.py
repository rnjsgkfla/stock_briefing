from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.bootstrap import DEMO_USER_ID
from app.db.models import Stock, WatchlistItem
from app.db.session import get_db_session
from app.schemas.broker import MarketQuote
from app.schemas.watchlist import WatchlistCreate, WatchlistStock
from app.services.broker import get_market_quotes
from app.services.market_data import STOCK_CATALOG, get_mock_quote, resolve_stock_symbol

router = APIRouter()
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]


async def _get_quotes_or_503(symbols: list[str]) -> dict[str, MarketQuote]:
    try:
        quotes = await get_market_quotes(symbols)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    missing = [symbol for symbol in symbols if symbol not in quotes]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"현재가를 받지 못한 종목입니다: {', '.join(missing)}",
        )
    return quotes


def _to_response(item: WatchlistItem, quote: MarketQuote) -> WatchlistStock:
    _, _, news_count = get_mock_quote(item.stock.symbol)
    display_price = (
        f"₩{quote.current_price:,.0f}"
        if quote.currency == "KRW"
        else f"${quote.current_price:,.2f}"
    )
    return WatchlistStock(
        symbol=item.stock.symbol,
        name=item.stock.name,
        market=item.stock.market,
        currency=item.stock.currency,
        current_price=quote.current_price,
        display_price=display_price,
        change_percent=quote.change_percent,
        news_count=news_count,
        added_at=item.created_at,
        price_provider=get_settings().market_data_provider,
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
    items = result.unique().all()
    quotes = await _get_quotes_or_503([item.stock.symbol for item in items])
    return [_to_response(item, quotes[item.stock.symbol]) for item in items]


@router.post("", response_model=WatchlistStock, status_code=status.HTTP_201_CREATED)
async def add_watchlist_stock(
    payload: WatchlistCreate,
    session: DatabaseSession,
) -> WatchlistStock:
    symbol = resolve_stock_symbol(payload.symbol)
    metadata = STOCK_CATALOG.get(symbol)
    if metadata is None:
        supported = ", ".join(sorted(STOCK_CATALOG))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"지원하지 않는 종목입니다. 현재 지원: {supported}",
        )

    quotes = await _get_quotes_or_503([symbol])

    stock = await session.scalar(select(Stock).where(Stock.symbol == symbol))
    if stock is None:
        stock = Stock(symbol=symbol, **metadata)
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
    return _to_response(item, quotes[symbol])


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
