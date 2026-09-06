from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.bootstrap import DEMO_USER_ID
from app.db.models import NewsArticle, Stock, WatchlistItem
from app.integrations.news_collector import AlphaVantageNewsCollector, MockNewsCollector
from app.schemas.news_feed import NewsRefreshResult


def get_news_collector():
    settings = get_settings()
    if settings.news_provider == "mock":
        return MockNewsCollector()

    api_key = settings.alpha_vantage_api_key
    if api_key is None or not api_key.get_secret_value():
        raise RuntimeError(
            "NEWS_PROVIDER=alpha_vantage일 때 ALPHA_VANTAGE_API_KEY가 필요합니다."
        )
    return AlphaVantageNewsCollector(api_key.get_secret_value())


async def refresh_news_feed(session: AsyncSession) -> NewsRefreshResult:
    symbols = list(
        await session.scalars(
            select(Stock.symbol)
            .join(WatchlistItem, WatchlistItem.stock_id == Stock.id)
            .where(WatchlistItem.user_id == DEMO_USER_ID)
            .order_by(Stock.symbol)
        )
    )
    collector = get_news_collector()
    collected = await collector.fetch(symbols)
    external_ids = [item.external_id for item in collected]
    existing_ids = set()
    if external_ids:
        existing_ids = set(
            await session.scalars(
                select(NewsArticle.external_id).where(NewsArticle.external_id.in_(external_ids))
            )
        )

    new_items = [item for item in collected if item.external_id not in existing_ids]
    session.add_all(
        [
            NewsArticle(
                external_id=item.external_id,
                title=item.title,
                summary=item.summary,
                source=item.source,
                source_url=item.source_url,
                published_at=item.published_at,
                symbols=item.symbols,
                sentiment=item.sentiment,
                provider=item.provider,
            )
            for item in new_items
        ]
    )
    await session.commit()
    return NewsRefreshResult(
        provider=collector.provider,
        collected_count=len(collected),
        stored_count=len(new_items),
        duplicate_count=len(collected) - len(new_items),
    )
