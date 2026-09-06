from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Protocol

import httpx


@dataclass(frozen=True)
class CollectedNews:
    external_id: str
    title: str
    summary: str
    source: str
    source_url: str
    published_at: datetime
    symbols: list[str]
    sentiment: str | None
    provider: str


class NewsCollector(Protocol):
    provider: str

    async def fetch(self, symbols: list[str]) -> list[CollectedNews]: ...


def _external_id(provider: str, source_url: str) -> str:
    return sha256(f"{provider}:{source_url}".encode()).hexdigest()


class MockNewsCollector:
    provider = "mock"

    async def fetch(self, symbols: list[str]) -> list[CollectedNews]:
        now = datetime.now(UTC)
        related = symbols[:2] or ["NVDA", "AMD"]
        samples = [
            (
                "미국 기술주 강세, 반도체 업종 중심으로 상승",
                "대형 기술주와 반도체 종목이 미국 증시 상승을 주도했습니다.",
                "Morning Bell Sample",
                "https://example.com/mock/us-semiconductor-rally",
                now - timedelta(hours=2),
                related,
                "Bullish",
            ),
            (
                "미국 장기 국채 금리 움직임에 성장주 변동성 확대",
                "장기 금리 변화로 성장주와 원·달러 환율의 장중 변동성이 커졌습니다.",
                "Morning Bell Sample",
                "https://example.com/mock/treasury-yield-volatility",
                now - timedelta(hours=4),
                related,
                "Neutral",
            ),
            (
                "국내 반도체 업종, 미국장 흐름과 환율 영향 주목",
                "국내장 개장을 앞두고 미국 반도체 지수와 원·달러 환율이 핵심 변수입니다.",
                "Morning Bell Sample",
                "https://example.com/mock/korea-opening-impact",
                now - timedelta(hours=6),
                ["005930", "000660"],
                "Neutral",
            ),
        ]
        return [
            CollectedNews(
                external_id=_external_id(self.provider, item[3]),
                title=item[0],
                summary=item[1],
                source=item[2],
                source_url=item[3],
                published_at=item[4],
                symbols=item[5],
                sentiment=item[6],
                provider=self.provider,
            )
            for item in samples
        ]


class AlphaVantageNewsCollector:
    provider = "alpha_vantage"

    def __init__(
        self,
        api_key: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._transport = transport

    async def fetch(self, symbols: list[str]) -> list[CollectedNews]:
        params = {
            "function": "NEWS_SENTIMENT",
            "sort": "LATEST",
            "limit": "50",
            "apikey": self._api_key,
        }
        us_symbols = [symbol for symbol in symbols if not symbol.isdigit()]
        if us_symbols:
            params["tickers"] = ",".join(us_symbols[:5])
        else:
            params["topics"] = "financial_markets"

        try:
            async with httpx.AsyncClient(timeout=15, transport=self._transport) as client:
                response = await client.get("https://www.alphavantage.co/query", params=params)
                response.raise_for_status()
                payload = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError("Alpha Vantage 서버에 연결하지 못했습니다.") from exc

        error = payload.get("Error Message") or payload.get("Note") or payload.get("Information")
        if error:
            raise RuntimeError(f"Alpha Vantage 뉴스 수집 실패: {error}")

        return [self._parse_item(item) for item in payload.get("feed", [])]

    def _parse_item(self, item: dict) -> CollectedNews:
        source_url = item["url"]
        published_at = datetime.strptime(item["time_published"], "%Y%m%dT%H%M%S").replace(
            tzinfo=UTC
        )
        symbols = [
            ticker["ticker"]
            for ticker in item.get("ticker_sentiment", [])
            if ticker.get("ticker")
        ]
        return CollectedNews(
            external_id=_external_id(self.provider, source_url),
            title=item.get("title", "제목 없음"),
            summary=item.get("summary", "요약 정보가 없습니다."),
            source=item.get("source", "Unknown"),
            source_url=source_url,
            published_at=published_at,
            symbols=symbols,
            sentiment=item.get("overall_sentiment_label"),
            provider=self.provider,
        )
