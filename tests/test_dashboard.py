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
    assert len(body["markets"]) == 5
    assert {market["symbol"] for market in body["markets"]} >= {"KOSPI", "KOSDAQ"}
    assert {session["market"] for session in body["market_sessions"]} == {"US", "KR"}
    assert body["holdings"][0]["symbol"] == "NVDA"
    assert {holding["market_group"] for holding in body["holdings"]} == {"US", "KR"}
    assert body["focus_items"][0]["evidence"]
