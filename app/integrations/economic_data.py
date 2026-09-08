import asyncio
import csv
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import StringIO
from time import monotonic

import httpx


@dataclass(frozen=True)
class EconomicMetric:
    value: float
    previous_value: float
    as_of: str

    @property
    def change_percent(self) -> float:
        if self.previous_value == 0:
            return 0
        return round((self.value - self.previous_value) / self.previous_value * 100, 2)


class AlphaVantageEconomicClient:
    def __init__(
        self,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._transport = transport

    async def get_treasury_yield(self) -> EconomicMetric:
        payload = await self._get(
            {
                "function": "TREASURY_YIELD",
                "interval": "daily",
                "maturity": "10year",
            }
        )
        values = [item for item in payload.get("data", []) if item.get("value") not in {None, "."}]
        if len(values) < 2:
            raise RuntimeError("미국 10년물 국채 금리 최신값을 확인하지 못했습니다.")
        return EconomicMetric(
            value=float(values[0]["value"]),
            previous_value=float(values[1]["value"]),
            as_of=values[0]["date"],
        )

    async def get_usd_krw(self) -> EconomicMetric:
        payload = await self._get(
            {
                "function": "FX_DAILY",
                "from_symbol": "USD",
                "to_symbol": "KRW",
                "outputsize": "compact",
            }
        )
        series = payload.get("Time Series FX (Daily)", {})
        dates = sorted(series, reverse=True)
        if len(dates) < 2:
            raise RuntimeError("원·달러 환율 최신값을 확인하지 못했습니다.")
        return EconomicMetric(
            value=float(series[dates[0]]["4. close"]),
            previous_value=float(series[dates[1]]["4. close"]),
            as_of=dates[0],
        )

    async def _get(self, params: dict[str, str]) -> dict:
        params["apikey"] = self._api_key
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                response = await client.get("https://www.alphavantage.co/query", params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError("Alpha Vantage 경제지표 서버에 연결하지 못했습니다.") from exc

        error = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if error:
            raise RuntimeError(f"Alpha Vantage 경제지표 조회 실패: {error}")
        return payload


class FredEconomicClient:
    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport

    async def get_treasury_yield(self) -> EconomicMetric:
        return await self._get_series("DGS10")

    async def get_nasdaq_composite(self) -> EconomicMetric:
        return await self._get_series("NASDAQCOM")

    async def get_sp500(self) -> EconomicMetric:
        return await self._get_series("SP500")

    async def _get_series(self, series_id: str) -> EconomicMetric:
        start_date = (datetime.now(UTC) - timedelta(days=14)).date().isoformat()
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                response = await client.get(
                    "https://fred.stlouisfed.org/graph/fredgraph.csv",
                    params={"id": series_id, "cosd": start_date},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"FRED {series_id} 서버에 연결하지 못했습니다.") from exc

        rows = [
            row
            for row in csv.DictReader(StringIO(response.text))
            if row.get(series_id) not in {None, "."}
        ]
        if len(rows) < 2:
            raise RuntimeError(f"FRED {series_id} 최신값을 확인하지 못했습니다.")
        return EconomicMetric(
            value=float(rows[-1][series_id]),
            previous_value=float(rows[-2][series_id]),
            as_of=rows[-1]["observation_date"],
        )


_metric_cache: tuple[float, dict[str, EconomicMetric]] | None = None
_cache_lock = asyncio.Lock()


async def get_cached_economic_metrics(api_key: str | None = None) -> dict[str, EconomicMetric]:
    global _metric_cache
    if _metric_cache and monotonic() - _metric_cache[0] < 21_600:
        return _metric_cache[1]

    async with _cache_lock:
        if _metric_cache and monotonic() - _metric_cache[0] < 21_600:
            return _metric_cache[1]
        fred_client = FredEconomicClient()
        treasury, nasdaq, sp500 = await asyncio.gather(
            fred_client.get_treasury_yield(),
            fred_client.get_nasdaq_composite(),
            fred_client.get_sp500(),
            return_exceptions=True,
        )
        if isinstance(treasury, Exception) and api_key:
            try:
                treasury = await AlphaVantageEconomicClient(api_key).get_treasury_yield()
            except RuntimeError:
                treasury = None

        metrics = {}
        for key, metric in (
            ("treasury", treasury),
            ("nasdaq", nasdaq),
            ("sp500", sp500),
        ):
            if isinstance(metric, EconomicMetric):
                metrics[key] = metric
        _metric_cache = (monotonic(), metrics)
        return metrics
