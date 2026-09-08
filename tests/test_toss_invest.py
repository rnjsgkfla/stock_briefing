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
        if request.url.path == "/api/v1/stocks":
            assert request.url.params["symbols"] == "NFLX"
            return httpx.Response(
                200,
                json={
                    "result": [
                        {
                            "symbol": "NFLX",
                            "name": "Netflix",
                            "market": "NASDAQ",
                            "currency": "USD",
                        }
                    ]
                },
            )
        if request.url.path == "/api/v1/exchange-rate":
            assert request.url.params["baseCurrency"] == "USD"
            assert request.url.params["quoteCurrency"] == "KRW"
            return httpx.Response(
                200,
                json={
                    "result": {
                        "rate": "1353.1",
                        "midRate": "1352.6",
                        "validFrom": "2026-09-07T01:09:58+09:00",
                    }
                },
            )
        if request.url.path == "/api/v1/market-indicators/prices":
            assert request.url.params["symbols"] == "KOSPI,KOSDAQ"
            return httpx.Response(
                200,
                json={
                    "result": [
                        {"symbol": "KOSPI", "lastPrice": "6954.52", "timestamp": None},
                        {"symbol": "KOSDAQ", "lastPrice": "811.88", "timestamp": None},
                    ]
                },
            )
        if request.url.path.startswith("/api/v1/market-indicators/"):
            symbol = request.url.path.split("/")[-2]
            previous_close = "6995.39" if symbol == "KOSPI" else "807.20"
            return httpx.Response(
                200,
                json={
                    "result": {
                        "candles": [
                            {
                                "timestamp": "2026-09-08T00:00:00+09:00",
                                "closePrice": "1",
                            },
                            {"closePrice": previous_close},
                        ]
                    }
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
    stock = await client.get_stock("NFLX")
    exchange_rate, exchange_rate_as_of = await client.get_exchange_rate()
    market_indicators = await client.get_market_indicators(["KOSPI", "KOSDAQ"])

    assert token_requests == 1
    assert accounts[0].account_seq == "1234"
    assert quotes["005930"].current_price == 72000
    assert quotes["005930"].change_percent == 2.86
    assert quotes["AAPL"].currency == "USD"
    assert quotes["AAPL"].change_percent == 5.25
    assert stock is not None
    assert stock.name == "Netflix"
    assert exchange_rate == 1352.6
    assert exchange_rate_as_of == "2026-09-07T01:09:58+09:00"
    assert market_indicators["KOSPI"].current_value == 6954.52
    assert market_indicators["KOSPI"].change_percent == -0.58
    assert market_indicators["KOSDAQ"].change_percent == 0.58
