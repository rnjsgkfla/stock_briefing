from sqlalchemy import select

from app.db.models import Stock, User, WatchlistItem
from app.db.session import async_session_factory
from app.services.market_data import STOCK_CATALOG

DEMO_USER_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_WATCHLIST = ("TSLA", "AMD")


async def seed_demo_data() -> None:
    async with async_session_factory() as session:
        user = await session.get(User, DEMO_USER_ID)
        if user is None:
            session.add(
                User(
                    id=DEMO_USER_ID,
                    email="demo@morningbell.local",
                    display_name="Demo Investor",
                )
            )

        existing = await session.scalar(
            select(WatchlistItem.id).where(WatchlistItem.user_id == DEMO_USER_ID).limit(1)
        )
        if existing is None:
            for symbol in DEFAULT_WATCHLIST:
                stock = await session.scalar(select(Stock).where(Stock.symbol == symbol))
                if stock is None:
                    metadata = STOCK_CATALOG[symbol]
                    stock = Stock(symbol=symbol, **metadata)
                    session.add(stock)
                    await session.flush()
                session.add(WatchlistItem(user_id=DEMO_USER_ID, stock_id=stock.id))

        await session.commit()
