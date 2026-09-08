from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_broker_accounts_uses_mock_provider_by_default() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/broker/accounts")

    assert response.status_code == 200
    assert response.json() == {"provider": "mock", "accounts": []}


async def test_broker_holdings_uses_demo_status_in_mock_mode() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/api/v1/broker/holdings")

    assert response.status_code == 200
    assert response.json()["status"] == "demo"
    assert response.json()["holdings"] == []
