from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_watchlist_crud_flow() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        initial = await client.get("/api/v1/watchlist")
        created = await client.post("/api/v1/watchlist", json={"symbol": "nvda"})
        duplicate = await client.post("/api/v1/watchlist", json={"symbol": "NVDA"})
        after_create = await client.get("/api/v1/watchlist")
        deleted = await client.delete("/api/v1/watchlist/NVDA")
        after_delete = await client.get("/api/v1/watchlist")

    assert initial.status_code == 200
    assert {item["symbol"] for item in initial.json()} == {"TSLA", "AMD"}
    assert created.status_code == 201
    assert created.json()["symbol"] == "NVDA"
    assert duplicate.status_code == 409
    assert {item["symbol"] for item in after_create.json()} == {"TSLA", "AMD", "NVDA"}
    assert deleted.status_code == 204
    assert {item["symbol"] for item in after_delete.json()} == {"TSLA", "AMD"}


async def test_watchlist_rejects_unsupported_symbol() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/watchlist", json={"symbol": "UNKNOWN"})

    assert response.status_code == 404
    assert "현재 지원" in response.json()["detail"]


async def test_watchlist_accepts_korean_stock_code() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.post("/api/v1/watchlist", json={"symbol": "삼성전자"})

    assert response.status_code == 201
    assert response.json()["symbol"] == "005930"
    assert response.json()["name"] == "삼성전자"
    assert response.json()["market"] == "KOSPI"
    assert response.json()["display_price"].startswith("₩")
