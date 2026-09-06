import httpx
import pytest

from app.integrations.toss_invest import TossInvestClient


@pytest.mark.asyncio
async def test_toss_client_reuses_token_and_maps_accounts_and_prices() -> None:
    token_requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal token_requests
        if request.url.path == "/oauth2/token":
            token_requests += 1
            return httpx.Response(
                200,
                json={"result": {"accessToken": "test-token", "expiresIn": 3600}},
            )
        assert request.headers["Authorization"] == "Bearer test-token"
        if request.url.path == "/api/v1/accounts":
            return httpx.Response(
                200,
                json={"result": [{"accountSeq": 1234, "accountName": "위탁계좌"}]},
            )
        if request.url.path == "/api/v1/prices":
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "symbol": "005930",
                            "lastPrice": "72000",
                            "currency": "KRW",
                            "timestamp": "2026-09-05T06:30:00Z",
                        },
                        {
                            "symbol": "AAPL",
                            "lastPrice": "210.50",
                            "currency": "USD",
                            "timestamp": "2026-09-05T20:00:00Z",
                        },
                    ]
                },
            )
        if request.url.path == "/api/v1/candles":
            previous_close = "70000" if request.url.params["symbol"] == "005930" else "200"
            return httpx.Response(
                200,
                json={
                    "result": {
                        "candles": [
                            {"closePrice": "1"},
                            {"closePrice": previous_close},
                        ]
                    }
                },
            )
        return httpx.Response(404)

    client = TossInvestClient(
        base_url="https://example.test",
        client_id="client-id",
        client_secret="client-secret",
        transport=httpx.MockTransport(handler),
    )

    accounts = await client.get_accounts()
    quotes = await client.get_prices(["005930", "AAPL"])

    assert token_requests == 1
    assert accounts[0].account_seq == "1234"
    assert quotes["005930"].current_price == 72000
    assert quotes["005930"].change_percent == 2.86
    assert quotes["AAPL"].currency == "USD"
    assert quotes["AAPL"].change_percent == 5.25
