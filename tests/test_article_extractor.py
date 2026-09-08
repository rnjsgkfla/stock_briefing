from datetime import UTC, datetime

import httpx

from app.db.models import NewsArticle
from app.integrations.article_extractor import (
    MAX_DOWNLOAD_BYTES,
    ArticleExtractor,
    ExtractionResult,
)
from app.services.news_extraction import extract_article_contents


async def test_article_extractor_extracts_main_text() -> None:
    paragraph = (
        "The semiconductor market rose after companies reported stronger demand for memory chips. "
        "Analysts also cited improving inventory conditions and continued data-center investment. "
    )
    html = (
        "<html><body><nav>menu</nav><article><h1>Market update</h1>"
        f"<p>{paragraph * 5}</p></article></body></html>"
    )

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=html, headers={"content-type": "text/html"})

    extractor = ArticleExtractor(
        transport=httpx.MockTransport(handler),
        enforce_public_network=False,
    )
    result = await extractor.extract("https://example.com/news")

    assert result.status == "success"
    assert result.text is not None
    assert "semiconductor market" in result.text
    assert result.content_hash is not None


async def test_article_extractor_blocks_private_network() -> None:
    result = await ArticleExtractor().extract("http://127.0.0.1/private")

    assert result.status == "blocked_address"


async def test_article_extractor_rejects_large_response() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text="not downloaded",
            headers={
                "content-type": "text/html",
                "content-length": str(MAX_DOWNLOAD_BYTES + 1),
            },
        )

    extractor = ArticleExtractor(
        transport=httpx.MockTransport(handler),
        enforce_public_network=False,
    )
    result = await extractor.extract("https://example.com/large")

    assert result.status == "too_large"


async def test_news_extraction_falls_back_when_body_is_unavailable() -> None:
    articles = [
        _article("success", "https://example.com/success"),
        _article("blocked", "https://example.com/blocked"),
    ]

    class FakeExtractor:
        async def extract(self, source_url: str) -> ExtractionResult:
            if source_url.endswith("success"):
                return ExtractionResult("success", "full article body", "content-hash")
            return ExtractionResult("http_error")

    contents, extracted_count = await extract_article_contents(articles, FakeExtractor())

    assert extracted_count == 1
    assert contents == {"success": "full article body"}
    assert articles[0].content_source == "extracted_body"
    assert articles[0].extraction_status == "success"
    assert articles[1].content_source == "provider_summary"
    assert articles[1].extraction_status == "http_error"


def _article(external_id: str, source_url: str) -> NewsArticle:
    return NewsArticle(
        external_id=external_id,
        title="Article title",
        summary="Provider summary",
        korean_summary=None,
        category="기타",
        source="Example",
        source_url=source_url,
        published_at=datetime.now(UTC),
        symbols=[],
        sentiment=None,
        provider="alpha_vantage",
    )
