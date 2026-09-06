from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_analyze_news_uses_mock_provider_by_default() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/news/analyze",
            json={
                "title": "반도체 기업의 신규 데이터센터 제품 발표",
                "content": (
                    "한 반도체 기업이 신규 데이터센터 제품을 공개하고 "
                    "하반기 공급 계획을 발표했습니다."
                ),
                "candidate_symbols": ["nvda", "NVDA", "amd"],
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "mock"
    assert body["related_symbols"] == ["NVDA", "AMD"]


async def test_analyze_news_rejects_short_content() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/v1/news/analyze",
            json={"title": "짧은 기사", "content": "너무 짧음"},
        )

    assert response.status_code == 422
