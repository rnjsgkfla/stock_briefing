import asyncio

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.integrations.gemini import GeminiNewsAnalyzer

CATEGORY_KEYWORDS = {
    "금리": ("treasury", "yield", "interest rate", "fed", "inflation", "cpi"),
    "환율": ("currency", "forex", "dollar", "won", "yen", "exchange rate"),
    "반도체": ("semiconductor", "chip", "nvidia", "amd", "intel", "hbm"),
    "실적": ("earnings", "revenue", "profit", "guidance", "quarterly"),
    "전쟁·지정학": ("war", "military", "conflict", "sanction", "israel", "iran", "ukraine"),
}


def categorize_news(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return category
    return "기업"


async def enrich_news_articles(
    articles: list[NewsArticle],
    article_contents: dict[str, str] | None = None,
) -> int:
    if not articles:
        return 0

    settings = get_settings()
    if settings.ai_provider == "mock":
        for article in articles:
            article.korean_summary = article.summary
            article.category = categorize_news(article.title, article.summary)
        return len(articles)

    api_key = settings.gemini_api_key
    if api_key is None or not api_key.get_secret_value():
        raise RuntimeError("AI_PROVIDER=gemini일 때 GEMINI_API_KEY가 필요합니다.")

    analyzer = GeminiNewsAnalyzer(
        api_key=api_key.get_secret_value(),
        model=settings.gemini_model,
    )
    contents = article_contents or {}
    inputs = [
        {
            "index": index,
            "title": article.title,
            "content": contents.get(article.external_id, article.summary),
            "content_source": article.content_source,
        }
        for index, article in enumerate(articles)
    ]
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            result = await asyncio.to_thread(analyzer.enrich, inputs)
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                await asyncio.sleep(2**attempt)
    else:
        raise RuntimeError("Gemini 뉴스 한국어 요약에 실패했습니다.") from last_error
    by_index = {item.index: item for item in result.items}
    enriched_count = 0
    for index, article in enumerate(articles):
        enrichment = by_index.get(index)
        if enrichment is None:
            continue
        article.korean_summary = enrichment.korean_summary
        article.category = (
            "환율" if "FOREX:USD" in article.symbols else enrichment.category
        )
        enriched_count += 1
    return enriched_count
