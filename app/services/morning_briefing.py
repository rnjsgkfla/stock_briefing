import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.integrations.economic_data import EconomicMetric, get_cached_economic_metrics
from app.schemas.broker import MarketQuote
from app.schemas.dashboard import DashboardSnapshot, FocusItem, MarketIndicator
from app.services.broker import (
    get_market_indicator_quotes,
    get_market_quotes,
    get_usd_krw_metric,
)
from app.services.market_data import get_dashboard_snapshot

SEMICONDUCTOR_SYMBOLS = ["NVDA", "AMD", "005930", "000660"]


def _format_quote(quote: MarketQuote) -> str:
    change = quote.change_percent
    change_text = "등락률 확인 불가" if change is None else f"{change:+.2f}%"
    price = (
        f"₩{quote.current_price:,.0f}"
        if quote.currency == "KRW"
        else f"${quote.current_price:,.2f}"
    )
    return f"{quote.symbol} {price} ({change_text})"


def _news_reason(
    news: list[NewsArticle],
    category: str,
    relevance_keywords: tuple[str, ...] = (),
    fallback_keywords: tuple[str, ...] = (),
) -> str:
    def relevance_score(item: NewsArticle, keywords: tuple[str, ...]) -> int:
        text = f"{item.title} {item.korean_summary or ''}".lower()
        return sum(text.count(keyword.lower()) for keyword in keywords)

    candidates = [item for item in news if item.category == category and item.korean_summary]
    article = (
        max(candidates, key=lambda item: relevance_score(item, relevance_keywords))
        if candidates
        else None
    )
    if article is None and fallback_keywords:
        fallback_candidates = [
            item
            for item in news
            if item.korean_summary
            and any(keyword in item.korean_summary for keyword in fallback_keywords)
        ]
        article = (
            max(
                fallback_candidates,
                key=lambda item: relevance_score(item, fallback_keywords),
            )
            if fallback_candidates
            else None
        )
    if article is None:
        return "관련 실제 뉴스의 한국어 요약이 아직 없습니다."
    return f"{article.source}: {article.korean_summary}"


def _metric_direction(metric: EconomicMetric) -> str:
    direction = "상승" if metric.value > metric.previous_value else "하락"
    return direction


def _to_market_indicator(
    symbol: str,
    name: str,
    metric: EconomicMetric,
    provider: str,
) -> MarketIndicator:
    return MarketIndicator(
        symbol=symbol,
        name=name,
        value=metric.value,
        display_value=f"{metric.value:,.2f}",
        change_percent=metric.change_percent,
        provider=provider,
        as_of=metric.as_of,
    )


async def build_dashboard_snapshot(session: AsyncSession) -> DashboardSnapshot:
    snapshot = get_dashboard_snapshot()
    news = list(
        await session.scalars(
            select(NewsArticle)
            .where(NewsArticle.provider == get_settings().news_provider)
            .order_by(NewsArticle.published_at.desc())
            .limit(200)
        )
    )

    settings = get_settings()
    alpha_key = (
        settings.alpha_vantage_api_key.get_secret_value()
        if settings.alpha_vantage_api_key
        else None
    )
    external_results = await asyncio.gather(
        get_market_quotes(SEMICONDUCTOR_SYMBOLS),
        get_cached_economic_metrics(alpha_key)
        if settings.market_data_provider == "toss"
        else asyncio.sleep(0, result={}),
        get_usd_krw_metric(),
        get_market_indicator_quotes(["KOSPI", "KOSDAQ"]),
        return_exceptions=True,
    )
    semiconductor_quotes = (
        external_results[0] if isinstance(external_results[0], dict) else {}
    )
    metrics: dict[str, EconomicMetric] = (
        external_results[1] if isinstance(external_results[1], dict) else {}
    )
    toss_usdkrw = (
        external_results[2] if isinstance(external_results[2], EconomicMetric) else None
    )
    toss_indices = external_results[3] if isinstance(external_results[3], dict) else {}
    if toss_usdkrw:
        metrics["usdkrw"] = toss_usdkrw

    market_updates: dict[str, MarketIndicator] = {}
    for key, symbol, name in (
        ("nasdaq", "IXIC", "NASDAQ Composite"),
        ("sp500", "SPX", "S&P 500"),
        ("usdkrw", "USDKRW", "USD / KRW"),
    ):
        metric = metrics.get(key)
        if metric:
            market_updates[symbol] = _to_market_indicator(
                symbol,
                name,
                metric,
                "toss" if key == "usdkrw" else "fred",
            )
    for symbol, quote in toss_indices.items():
        market_updates[symbol] = MarketIndicator(
            symbol=symbol,
            name=symbol,
            value=quote.current_value,
            display_value=f"{quote.current_value:,.2f}",
            change_percent=quote.change_percent,
            provider="toss",
            as_of=quote.timestamp,
        )
    markets = [market_updates.get(item.symbol, item) for item in snapshot.markets]
    actual_market_changes = [
        f"{item.name} {item.change_percent:+.2f}%"
        for item in markets
        if item.provider != "mock" and item.change_percent is not None
    ]
    market_summary = (
        " · ".join(actual_market_changes)
        if actual_market_changes
        else snapshot.summary
    )

    quote_evidence = [_format_quote(quote) for quote in semiconductor_quotes.values()]
    valid_changes = [
        quote.change_percent
        for quote in semiconductor_quotes.values()
        if quote.change_percent is not None
    ]
    average_change = sum(valid_changes) / len(valid_changes) if valid_changes else None
    semiconductor_description = (
        f"관련 종목 평균 등락률 {average_change:+.2f}%"
        if average_change is not None
        else "관련 종목 등락률 확인 불가"
    )

    treasury = metrics.get("treasury")
    treasury_direction = _metric_direction(treasury) if treasury else ""
    treasury_change_bps = (treasury.value - treasury.previous_value) * 100 if treasury else None
    treasury_description = (
        f"미국 10년물 {treasury.value:.2f}% · 전일 대비 {treasury_change_bps:+.1f}bp"
        if treasury
        else "미국 10년물 금리 확인 불가"
    )
    usdkrw = metrics.get("usdkrw")
    usdkrw_description = (
        f"USD/KRW {usdkrw.value:,.2f}원 · {usdkrw.change_percent:+.2f}%"
        if usdkrw
        else "원·달러 환율 확인 불가"
    )

    focus_items = [
        FocusItem(
            title="반도체 업종 반등 지속 여부",
            description=semiconductor_description,
            detail_summary=_news_reason(
                news,
                "반도체",
                ("반도체", "semiconductor", "chip", "메모리", "dram", "nand"),
            ),
            evidence=quote_evidence or ["토스증권 시세를 불러오지 못했습니다."],
            related_symbols=list(semiconductor_quotes) or SEMICONDUCTOR_SYMBOLS,
        ),
        FocusItem(
            title="미국 장기 국채 금리",
            description=treasury_description,
            detail_summary=_news_reason(
                news,
                "금리",
                (
                    f"국채 금리가 {treasury_direction}",
                    f"채권 금리가 {treasury_direction}",
                    "10년물",
                    "treasury",
                    "yield",
                ),
            ),
            evidence=(
                [
                    f"10년물 금리 {treasury.previous_value:.2f}% → "
                    f"{treasury.value:.2f}% ({_metric_direction(treasury)}), "
                    f"기준일 {treasury.as_of}"
                ]
                if treasury
                else ["경제지표 제공자에서 최신 금리를 받지 못했습니다."]
            ),
            related_symbols=["US10Y", "IXIC"],
        ),
        FocusItem(
            title="원·달러 환율",
            description=usdkrw_description,
            detail_summary=_news_reason(
                news,
                "환율",
                fallback_keywords=("강달러", "약달러", "달러화", "원화", "환율"),
            ),
            evidence=(
                [
                    f"USD/KRW {usdkrw.previous_value:,.2f}원 → "
                    f"{usdkrw.value:,.2f}원 ({_metric_direction(usdkrw)}), "
                    f"기준일 {usdkrw.as_of}"
                ]
                if usdkrw
                else ["경제지표 제공자에서 최신 환율을 받지 못했습니다."]
            ),
            related_symbols=["USDKRW", "KOSPI", "KOSDAQ"],
        ),
    ]
    return snapshot.model_copy(
        update={
            "summary": market_summary,
            "markets": markets,
            "focus_items": focus_items,
        }
    )
