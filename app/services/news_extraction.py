import asyncio
from datetime import UTC, datetime

from app.db.models import NewsArticle
from app.integrations.article_extractor import ArticleExtractor

EXTRACTION_LIMIT = 10
EXTRACTION_CONCURRENCY = 3


async def extract_article_contents(
    articles: list[NewsArticle],
    extractor: ArticleExtractor | None = None,
) -> tuple[dict[str, str], int]:
    targets = [article for article in articles if article.provider != "mock"][:EXTRACTION_LIMIT]
    if not targets:
        return {}, 0

    active_extractor = extractor or ArticleExtractor()

    semaphore = asyncio.Semaphore(EXTRACTION_CONCURRENCY)

    async def extract_one(article: NewsArticle):
        async with semaphore:
            return await active_extractor.extract(article.source_url)

    results = await asyncio.gather(
        *(extract_one(article) for article in targets),
        return_exceptions=True,
    )
    contents: dict[str, str] = {}
    extracted_count = 0
    extracted_at = datetime.now(UTC)
    for article, result in zip(targets, results, strict=True):
        article.extracted_at = extracted_at
        if isinstance(result, Exception):
            article.extraction_status = "extraction_error"
            article.content_source = "provider_summary"
            article.content_hash = None
            continue

        article.extraction_status = result.status
        if result.status == "success" and result.text:
            article.content_source = "extracted_body"
            article.content_hash = result.content_hash
            contents[article.external_id] = result.text
            extracted_count += 1
        else:
            article.content_source = "provider_summary"
            article.content_hash = None

    return contents, extracted_count
