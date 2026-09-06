from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_dashboard_returns_market_snapshot() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/dashboard")

    assert response.status_code == 200
    body = response.json()
    assert body["sample_data"] is True
    assert len(body["markets"]) == 3
    assert body["holdings"][0]["symbol"] == "NVDA"
