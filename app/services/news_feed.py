from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.bootstrap import DEMO_USER_ID
from app.db.models import NewsArticle, Stock, WatchlistItem
from app.integrations.news_collector import AlphaVantageNewsCollector, MockNewsCollector
from app.schemas.news_feed import NewsRefreshResult
from app.services.news_enrichment import categorize_news, enrich_news_articles
from app.services.news_extraction import extract_article_contents


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
                category=categorize_news(item.title, item.summary),
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
    await session.flush()
    provider_articles = list(
        await session.scalars(
            select(NewsArticle)
            .where(NewsArticle.provider == collector.provider)
            .order_by(NewsArticle.published_at.desc())
            .limit(200)
        )
    )
    for article in provider_articles:
        if "FOREX:USD" in article.symbols:
            article.category = "환율"
    pending_result = await session.scalars(
        select(NewsArticle)
        .where(
            NewsArticle.provider == collector.provider,
            NewsArticle.korean_summary.is_(None),
        )
        .order_by(NewsArticle.published_at.desc())
        .limit(20)
    )
    pending_articles = list(pending_result)
    article_contents: dict[str, str] = {}
    extracted_count = 0
    if get_settings().ai_provider == "gemini":
        article_contents, extracted_count = await extract_article_contents(pending_articles)
    try:
        summarized_count = await enrich_news_articles(pending_articles, article_contents)
    except RuntimeError:
        summarized_count = 0
    await session.commit()
    return NewsRefreshResult(
        provider=collector.provider,
        collected_count=len(collected),
        stored_count=len(new_items),
        duplicate_count=len(collected) - len(new_items),
        extracted_count=extracted_count,
        summarized_count=summarized_count,
    )
