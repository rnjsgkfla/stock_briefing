import httpx

from app.integrations.economic_data import AlphaVantageEconomicClient, FredEconomicClient


async def test_alpha_vantage_economic_metrics_parse_latest_values() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params["function"] == "TREASURY_YIELD":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"date": "2026-09-04", "value": "4.20"},
                        {"date": "2026-09-03", "value": "4.15"},
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "Time Series FX (Daily)": {
                    "2026-09-04": {"4. close": "1380.00"},
                    "2026-09-03": {"4. close": "1375.00"},
                }
            },
        )

    client = AlphaVantageEconomicClient(
        "test-key",
        transport=httpx.MockTransport(handler),
    )
    treasury = await client.get_treasury_yield()
    usdkrw = await client.get_usd_krw()

    assert treasury.value == 4.2
    assert treasury.change_percent == 1.2
    assert usdkrw.value == 1380
    assert usdkrw.change_percent == 0.36


async def test_fred_treasury_yield_uses_latest_non_empty_rows() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            text=(
                "observation_date,DGS10\n"
                "2026-09-02,4.79\n"
                "2026-09-03,4.77\n"
                "2026-09-04,.\n"
            ),
        )

    metric = await FredEconomicClient(
        transport=httpx.MockTransport(handler)
    ).get_treasury_yield()

    assert metric.value == 4.77
    assert metric.previous_value == 4.79
    assert metric.as_of == "2026-09-03"


async def test_fred_market_index_uses_requested_series() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        series_id = request.url.params["id"]
        assert series_id == "NASDAQCOM"
        return httpx.Response(
            200,
            text=(
                "observation_date,NASDAQCOM\n"
                "2026-09-03,26370.89\n"
                "2026-09-04,26502.10\n"
            ),
        )

    metric = await FredEconomicClient(
        transport=httpx.MockTransport(handler)
    ).get_nasdaq_composite()

    assert metric.value == 26502.1
    assert metric.change_percent == 0.5
