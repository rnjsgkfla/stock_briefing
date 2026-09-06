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
        start_date = (datetime.now(UTC) - timedelta(days=14)).date().isoformat()
        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                response = await client.get(
                    "https://fred.stlouisfed.org/graph/fredgraph.csv",
                    params={"id": "DGS10", "cosd": start_date},
                )
                response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError("FRED 미국 10년물 금리 서버에 연결하지 못했습니다.") from exc

        rows = [
            row
            for row in csv.DictReader(StringIO(response.text))
            if row.get("DGS10") not in {None, "."}
        ]
        if len(rows) < 2:
            raise RuntimeError("FRED 미국 10년물 금리 최신값을 확인하지 못했습니다.")
        return EconomicMetric(
            value=float(rows[-1]["DGS10"]),
            previous_value=float(rows[-2]["DGS10"]),
            as_of=rows[-1]["observation_date"],
        )


_metric_cache: tuple[float, dict[str, EconomicMetric]] | None = None
_cache_lock = asyncio.Lock()


async def get_cached_economic_metrics(api_key: str) -> dict[str, EconomicMetric]:
    global _metric_cache
    if _metric_cache and monotonic() - _metric_cache[0] < 21_600:
        return _metric_cache[1]

    async with _cache_lock:
        if _metric_cache and monotonic() - _metric_cache[0] < 21_600:
            return _metric_cache[1]
        alpha_client = AlphaVantageEconomicClient(api_key)
        try:
            treasury = await FredEconomicClient().get_treasury_yield()
        except RuntimeError:
            try:
                treasury = await alpha_client.get_treasury_yield()
            except RuntimeError:
                treasury = None
        metrics = {"treasury": treasury} if treasury else {}
        _metric_cache = (monotonic(), metrics)
        return metrics
