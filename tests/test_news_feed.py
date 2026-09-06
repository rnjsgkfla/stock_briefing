import httpx
from httpx import ASGITransport, AsyncClient

from app.integrations.news_collector import AlphaVantageNewsCollector
from app.main import app


async def test_refresh_news_stores_and_deduplicates_articles() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        first = await client.post("/api/v1/news/refresh")
        second = await client.post("/api/v1/news/refresh")
        latest = await client.get("/api/v1/news/latest")

    assert first.status_code == 200
    assert first.json() == {
        "provider": "mock",
        "collected_count": 3,
        "stored_count": 3,
        "duplicate_count": 0,
        "summarized_count": 3,
    }
    assert second.status_code == 200
    assert second.json()["stored_count"] == 0
    assert second.json()["duplicate_count"] == 3
    assert latest.status_code == 200
    assert len(latest.json()) == 3
    assert latest.json()[0]["provider"] == "mock"
    assert latest.json()[0]["korean_summary"]
    assert latest.json()[0]["category"]


async def test_latest_news_validates_limit() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/news/latest?limit=100")

    assert response.status_code == 422


async def test_alpha_vantage_excludes_korean_codes_from_ticker_filter() -> None:
    requested_filters: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if "tickers" in request.url.params:
            requested_filters.append(request.url.params["tickers"])
        else:
            requested_filters.append(request.url.params["topics"])
        return httpx.Response(
            200,
            json={
                "feed": [
                    {
                        "title": "Chip stocks move after market update",
                        "summary": "Semiconductor shares moved after a new market update.",
                        "source": "Example News",
                        "url": "https://example.com/actual-news",
                        "time_published": "20260907T010000",
                        "ticker_sentiment": [{"ticker": "NVDA"}],
                        "overall_sentiment_label": "Neutral",
                    }
                ]
            },
        )

    collector = AlphaVantageNewsCollector(
        "test-key",
        transport=httpx.MockTransport(handler),
    )
    articles = await collector.fetch(["005930", "AMD", "NVDA"])

    assert len(articles) == 1
    assert articles[0].provider == "alpha_vantage"
    assert articles[0].symbols == ["NVDA"]
    assert requested_filters == [
        "AMD,NVDA",
        "economy_monetary,financial_markets",
        "FOREX:USD",
    ]
